# library_management/tasks.py
# All scheduled functions live here
# This file is referenced in hooks.py

import frappe
from frappe.utils import today, date_diff


def calculate_overdue_fines():
    """
    Scheduled job: runs daily.
    Finds all submitted Issue transactions that are past due date
    and calculates/updates the fine amount.

    Fine rate: ₹5 per day after due date.
    """
    fine_per_day = 5  # ₹5 per day

    # Get all submitted Issue transactions that are overdue
    # docstatus = 1 means Submitted
    # due_date < today means overdue
    overdue_transactions = frappe.db.get_all(
        "Book Transaction",
        filters={
            "transaction_type": "Issue",
            "docstatus": 1,
            "due_date": ["<", today()],
        },
        fields=["name", "due_date", "library_member", "book_title", "member_name"]
    )

    if not overdue_transactions:
        # Nothing overdue today, exit cleanly
        return

    for txn in overdue_transactions:
        # Calculate how many days overdue
        days_overdue = date_diff(today(), txn.due_date)

        # Calculate fine
        fine_amount = days_overdue * fine_per_day

        # Update the fine_amount field on the transaction
        # We use db.set_value to avoid triggering the full save lifecycle
        frappe.db.set_value(
            "Book Transaction",
            txn.name,
            "fine_amount",
            fine_amount,
            update_modified=False
        )

    # Commit all DB changes in one transaction for performance
    frappe.db.commit()

    # Log how many records were updated (visible in Frappe Error Log)
    frappe.logger().info(
        f"Fine calculation complete. "
        f"Updated {len(overdue_transactions)} overdue transactions."
    )


def send_overdue_reminders():
    """
    Scheduled job: runs daily.
    Sends reminder emails to members with overdue books.
    Runs AFTER calculate_overdue_fines so fine amounts are fresh.
    """
    overdue_transactions = frappe.db.get_all(
        "Book Transaction",
        filters={
            "transaction_type": "Issue",
            "docstatus": 1,
            "due_date": ["<", today()],
        },
        fields=[
            "name", "due_date", "fine_amount",
            "library_member", "book_title", "member_name"
        ]
    )

    for txn in overdue_transactions:
        member_email = frappe.db.get_value(
            "Library Member",
            txn.library_member,
            "email"
        )

        if not member_email:
            continue

        days_overdue = date_diff(today(), txn.due_date)

        subject = f"OVERDUE NOTICE: Please Return '{txn.book_title}'"

        message = f"""
        <p>Dear {txn.member_name},</p>

        <p style="color:red;"><b>Your borrowed book is overdue!</b></p>

        <table border="1" cellpadding="8" cellspacing="0"
               style="border-collapse:collapse;">
            <tr><td><b>Book</b></td><td>{txn.book_title}</td></tr>
            <tr><td><b>Due Date</b></td><td>{txn.due_date}</td></tr>
            <tr><td><b>Days Overdue</b></td><td>{days_overdue} days</td></tr>
            <tr><td><b>Fine Accumulated</b></td>
                <td style="color:red;">₹{txn.fine_amount}</td></tr>
        </table>

        <p>Please return the book immediately to stop further fines.</p>

        <p>Thank you,<br>Library Management System</p>
        """

        frappe.sendmail(
            recipients=[member_email],
            subject=subject,
            message=message,
            now=False
        )


def expire_memberships():
    """
    Scheduled job: runs daily.
    Automatically sets membership_status to 'Expired'
    for members whose membership_end_date has passed.
    """
    # Find all Active members whose end date has passed
    expired_members = frappe.db.get_all(
        "Library Member",
        filters={
            "membership_status": "Active",
            "membership_end_date": ["<", today()]
        },
        fields=["name", "full_name"]
    )

    for member in expired_members:
        frappe.db.set_value(
            "Library Member",
            member.name,
            "membership_status",
            "Expired",
            update_modified=False
        )

    if expired_members:
        frappe.db.commit()
        frappe.logger().info(
            f"Expired {len(expired_members)} memberships."
        )

