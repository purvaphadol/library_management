# Copyright (c) 2024, Purva and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, date_diff


class BookTransaction(Document):

    def validate(self):
        """
        Runs every time the document is saved (Draft stage).
        Use this for business rule validation.
        If you raise frappe.ValidationError, the save is aborted
        and the error message is shown to the user in the browser.
        """
        if self.transaction_type == "Issue":
            self.validate_book_availability()
            self.validate_member_membership()
            self.set_due_date()

        if self.transaction_type == "Return":
            self.validate_return()

    def validate_book_availability(self):
        """
        Check if the book has copies available before issuing.
        We query the Book doctype directly using frappe.db.get_value.
        """
        # frappe.db.get_value(DocType, name_of_record, field_to_fetch)
        # Returns the value of that single field
        available = frappe.db.get_value("Book", self.book, "available_copies")

        if available is None:
            # Book record doesn't exist (shouldn't happen due to Link validation, but be safe)
            frappe.throw(
                f"Book {self.book} not found in the system.",
                title="Book Not Found"
            )

        if available <= 0:
            # frappe.throw raises ValidationError AND shows a red popup in the browser
            # The save is completely aborted - nothing writes to DB
            frappe.throw(
                f"Book <b>{self.book_title}</b> is currently not available. "
                f"All {frappe.db.get_value('Book', self.book, 'total_copies')} "
                f"copies are issued.",
                title="Book Not Available"
            )

    def validate_member_membership(self):
        """
        Check if the member's membership is still Active.
        An expired member cannot borrow books.
        """
        member_status = frappe.db.get_value(
            "Library Member",
            self.library_member,
            "membership_status"
        )

        if member_status != "Active":
            frappe.throw(
                f"Member <b>{self.member_name}</b> has a '{member_status}' membership. "
                f"Only Active members can borrow books. "
                f"Please renew the membership first.",
                title="Membership Inactive"
            )

    def set_due_date(self):
        """
        Auto-set due date to 14 days from transaction date if not set.
        This is a convenience — librarian can override if needed.
        """
        if not self.due_date:
            from frappe.utils import add_days
            self.due_date = add_days(self.transaction_date or today(), 14)

    def validate_return(self):
        """
        For Return transactions, verify there is an actual Issue transaction
        for this member-book combination that hasn't been returned yet.
        """
        # Check if there's a submitted Issue transaction for this book + member
        existing_issue = frappe.db.exists(
            "Book Transaction",
            {
                "book": self.book,
                "library_member": self.library_member,
                "transaction_type": "Issue",
                "docstatus": 1,  # 1 = Submitted
            }
        )

        if not existing_issue:
            frappe.throw(
                f"No active issue found for book <b>{self.book_title}</b> "
                f"and member <b>{self.member_name}</b>. "
                f"Cannot process return.",
                title="No Active Issue Found"
            )

    def on_submit(self):
        """
        Runs ONLY when the document is Submitted (not just saved).
        At this point the transaction is official.
        This is where we update book availability.
        """
        if self.transaction_type == "Issue":
            self.update_book_availability(action="issue")
            self.send_issue_confirmation_email()

        elif self.transaction_type == "Return":
            self.update_book_availability(action="return")
            self.set_return_date()

    def on_cancel(self):
        """
        Runs when a submitted document is Cancelled.
        We must REVERSE whatever on_submit did.
        """
        if self.transaction_type == "Issue":
            # Book was issued, now transaction is cancelled → give copy back
            self.update_book_availability(action="return")

        elif self.transaction_type == "Return":
            # Return was cancelled → book is issued again
            self.update_book_availability(action="issue")

    def update_book_availability(self, action):
        """
        Increment or decrement available_copies on the Book record.
        Using frappe.db.set_value is the correct approach here because:
        1. It directly updates the DB without triggering Book's own validate
        2. It's atomic and safe
        3. We pass update_modified=False to not change the Book's modified timestamp
        """
        book_doc = frappe.get_doc("Book", self.book)

        if action == "issue":
            new_count = book_doc.available_copies - 1
            new_status = "Available" if new_count > 0 else "Issued"
        else:  # return
            new_count = book_doc.available_copies + 1
            # Cap at total_copies (safety check)
            new_count = min(new_count, book_doc.total_copies)
            new_status = "Available"

        frappe.db.set_value(
            "Book",
            self.book,
            {
                "available_copies": new_count,
                "status": new_status
            },
            update_modified=False
        )

        # Clear cache for this book record so UI shows updated values immediately
        frappe.clear_cache(doctype="Book")

    def send_issue_confirmation_email(self):
        """
        Send confirmation email to member when book is officially issued.
        Uses Frappe's built-in sendmail which handles:
        - Email queue (doesn't block the request)
        - Retry on failure
        - Email logs visible in UI
        """
        # Fetch member's email
        member_email = frappe.db.get_value(
            "Library Member",
            self.library_member,
            "email"
        )

        if not member_email:
            # Log a warning but don't fail the entire submit
            frappe.log_error(
                f"No email found for member {self.library_member}",
                "Book Issue Email Failed"
            )
            return

        # Build the email body
        subject = f"Book Issued: {self.book_title}"

        message = f"""
        <p>Dear {self.member_name},</p>

        <p>Your book has been successfully issued. Here are the details:</p>

        <table border="1" cellpadding="8" cellspacing="0" 
               style="border-collapse:collapse; width:100%;">
            <tr>
                <td><b>Book Title</b></td>
                <td>{self.book_title}</td>
            </tr>
            <tr>
                <td><b>Transaction ID</b></td>
                <td>{self.name}</td>
            </tr>
            <tr>
                <td><b>Issue Date</b></td>
                <td>{self.transaction_date}</td>
            </tr>
            <tr>
                <td><b>Due Date</b></td>
                <td>{self.due_date}</td>
            </tr>
        </table>

        <p>Please return the book by the due date to avoid fines.</p>
        <p>Fine rate: ₹5 per day after due date.</p>

        <p>Thank you,<br>Library Management System</p>
        """

        frappe.sendmail(
            recipients=[member_email],
            subject=subject,
            message=message,
            now=False   # False = goes to email queue (non-blocking, recommended)
                        # True  = sends immediately (blocks request, use only for urgent)
        )

    def set_return_date(self):
        """Set return date to today when return transaction is submitted."""
        frappe.db.set_value(
            "Book Transaction",
            self.name,
            "return_date",
            today(),
            update_modified=False
        )

