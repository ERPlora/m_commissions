"""
Commissions module manifest.

Sales commission rules, tracking, payouts, and adjustments for staff members.
"""


# ---------------------------------------------------------------------------
# Module identity
# ---------------------------------------------------------------------------
MODULE_ID = "commissions"
MODULE_NAME = "Commissions"
MODULE_VERSION = "1.0.4"
MODULE_ICON = "wallet-outline"
MODULE_DESCRIPTION = "Sales commission rules, tracking, and payouts"
MODULE_AUTHOR = "ERPlora"
MODULE_CATEGORY = "sales"

# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------
HAS_MODELS = True
MIDDLEWARE = ""

# ---------------------------------------------------------------------------
# Menu (sidebar entry)
# ---------------------------------------------------------------------------
MENU = {
    "label": "Commissions",
    "icon": "wallet-outline",
    "order": 55,
}

# ---------------------------------------------------------------------------
# Navigation tabs (bottom tabbar in module views)
# ---------------------------------------------------------------------------
NAVIGATION = [
    {"id": "dashboard", "label": "Overview", "icon": "stats-chart-outline", "view": "dashboard"},
    {"id": "transactions", "label": "Transactions", "icon": "receipt-outline", "view": "transactions"},
    {"id": "payouts", "label": "Payouts", "icon": "cash-outline", "view": "payouts"},
    {"id": "rules", "label": "Rules", "icon": "options-outline", "view": "rules"},
    {"id": "adjustments", "label": "Adjustments", "icon": "swap-horizontal-outline", "view": "adjustments"},
    {"id": "settings", "label": "Settings", "icon": "settings-outline", "view": "settings"},
]

# ---------------------------------------------------------------------------
# Dependencies (other modules required to be active)
# ---------------------------------------------------------------------------
DEPENDENCIES: list[str] = ["staff", "services", "inventory", "sales", "appointments"]

# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
PERMISSIONS = [
    ("view_transaction", "View commission transactions"),
    ("add_transaction", "Add commission transactions"),
    ("approve_transaction", "Approve commission transactions"),
    ("view_rule", "View commission rules"),
    ("add_rule", "Add commission rules"),
    ("change_rule", "Edit commission rules"),
    ("delete_rule", "Delete commission rules"),
    ("view_payout", "View payouts"),
    ("add_payout", "Create payouts"),
    ("approve_payout", "Approve payouts"),
    ("process_payout", "Process payouts"),
    ("view_adjustment", "View adjustments"),
    ("add_adjustment", "Add adjustments"),
    ("delete_adjustment", "Delete adjustments"),
    ("manage_settings", "Manage commission settings"),
]

ROLE_PERMISSIONS = {
    "admin": ["*"],
    "manager": [
        "view_transaction", "approve_transaction",
        "view_rule", "add_rule", "change_rule",
        "view_payout", "add_payout", "approve_payout", "process_payout",
        "view_adjustment", "add_adjustment",
    ],
    "employee": [
        "view_transaction",
        "view_rule",
        "view_payout",
        "view_adjustment",
    ],
}

# ---------------------------------------------------------------------------
# Scheduled tasks
# ---------------------------------------------------------------------------
SCHEDULED_TASKS: list[dict] = []

# ---------------------------------------------------------------------------
# Pricing (free module)
# ---------------------------------------------------------------------------
# PRICING = {"monthly": 0, "yearly": 0}
