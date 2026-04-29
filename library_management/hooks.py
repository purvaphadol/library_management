# hooks.py
# This file wires your app into Frappe's lifecycle

app_name = "library_management"
app_title = "Library Management"
app_publisher = "Purva"
app_description = "A complete library management system for tracking books, members, and transactions."
app_email = "purva@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------
web_include_css = "/assets/library_management/css/login.css"

# ──────────────────────────────────────────────
# SCHEDULED JOBS
# ──────────────────────────────────────────────
scheduler_events = {
    "daily": [
        "library_management.tasks.calculate_overdue_fines",
        "library_management.tasks.send_overdue_reminders",
        "library_management.tasks.expire_memberships",
    ],
}

# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────
fixtures = [
    {
        "dt": "Role",
        "filters": [
            ["name", "in", ["Librarian", "Library Member"]]
        ]
    }
]
