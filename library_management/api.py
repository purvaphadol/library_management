# library_management/api.py
# Public API endpoints for the Library Management System

import frappe


@frappe.whitelist(allow_guest=True)
def get_library_stats():
    """
    Public endpoint — no login required (allow_guest=True).
    Returns basic library statistics for the login page.

    @frappe.whitelist() is REQUIRED for any function called via /api/method/
    Without it, Frappe returns 403 Forbidden.

    allow_guest=True means even non-logged-in users can call this.
    Use this ONLY for non-sensitive public data.
    """
    total_books = frappe.db.count("Book")
    total_members = frappe.db.count("Library Member")
    books_issued = frappe.db.count(
        "Book Transaction",
        filters={
            "transaction_type": "Issue",
            "docstatus": 1
        }
    )

    return {
        "total_books": total_books,
        "total_members": total_members,
        "books_issued": books_issued
    }
