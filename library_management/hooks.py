# hooks.py
# This file wires your app into Frappe's lifecycle

app_name = "library_management"
app_title = "Library Management"
app_publisher = "Purva"
app_description = "A complete library management system for tracking books, members, and transactions."
app_email = "purva@gmail.com"
app_license = "MIT"

# ──────────────────────────────────────────────
# SCHEDULED JOBS
# ──────────────────────────────────────────────
# These run automatically at the specified intervals.
# Format: "module_path.function_name"
# The scheduler must be running (bench start runs it via Procfile)
#
# Available intervals:
#   all          → every 5 minutes
#   hourly       → every hour
#   daily        → once per day (midnight)
#   weekly       → once per week
#   monthly      → once per month
#   cron         → custom cron expression

scheduler_events = {
    "daily": [
        # Step 1: Calculate fines first
        "library_management.tasks.calculate_overdue_fines",
        # Step 2: Then send reminders (fines are already updated)
        "library_management.tasks.send_overdue_reminders",
        # Step 3: Expire old memberships
        "library_management.tasks.expire_memberships",
    ],
    # Example of custom cron (runs at 9 AM every day):
    # "cron": {
    #     "0 9 * * *": [
    #         "library_management.tasks.send_morning_report"
    #     ]
    # }
}

# ──────────────────────────────────────────────
# DOC EVENTS (Alternative to controller methods)
# ──────────────────────────────────────────────
# You can also hook into DocType events FROM hooks.py
# instead of writing in the controller .py file.
# Use this when you want ONE app to react to ANOTHER app's DocType.
# For your OWN doctypes, use the controller file (book_transaction.py).
#
# Example (commented out — already handled in controller):
# doc_events = {
#     "Book Transaction": {
#         "on_submit": "library_management.tasks.on_book_transaction_submit",
#     }
# }

# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────
# Fixtures are records that get exported to JSON and
# imported automatically during bench migrate.
# We'll use this in Phase 4.
fixtures = [
    {
        "dt": "Role",
        "filters": [
            ["name", "in", ["Librarian", "Library Member"]]
        ]
    }
]

# ──────────────────────────────────────────────
# WEBSITE ROUTE RULES (Phase 5)
# ──────────────────────────────────────────────
# website_route_rules = [
#     {"from_route": "/library", "to_route": "library"}
# ]

