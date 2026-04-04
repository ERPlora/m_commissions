"""
Commissions module manifest.

Sales commission rules, tracking, payouts, and adjustments for staff members.
"""

from app.core.i18n import LazyString

# ---------------------------------------------------------------------------
# Module identity
# ---------------------------------------------------------------------------
MODULE_ID = "commissions"
MODULE_NAME = LazyString("Commissions", module_id="commissions")
MODULE_VERSION = "1.0.1"
MODULE_ICON = "wallet-outline"
MODULE_DESCRIPTION = LazyString(
    "Sales commission rules, tracking, and payouts",
    module_id="commissions",
)
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
    "label": LazyString("Commissions", module_id="commissions"),
    "icon": "wallet-outline",
    "order": 55,
}

# ---------------------------------------------------------------------------
# Navigation tabs (bottom tabbar in module views)
# ---------------------------------------------------------------------------
NAVIGATION = [
    {"id": "dashboard", "label": LazyString("Overview", module_id="commissions"), "icon": "stats-chart-outline", "view": "dashboard"},
    {"id": "transactions", "label": LazyString("Transactions", module_id="commissions"), "icon": "receipt-outline", "view": "transactions"},
    {"id": "payouts", "label": LazyString("Payouts", module_id="commissions"), "icon": "cash-outline", "view": "payouts"},
    {"id": "rules", "label": LazyString("Rules", module_id="commissions"), "icon": "options-outline", "view": "rules"},
    {"id": "adjustments", "label": LazyString("Adjustments", module_id="commissions"), "icon": "swap-horizontal-outline", "view": "adjustments"},
    {"id": "settings", "label": LazyString("Settings", module_id="commissions"), "icon": "settings-outline", "view": "settings"},
]

# ---------------------------------------------------------------------------
# Dependencies (other modules required to be active)
# ---------------------------------------------------------------------------
DEPENDENCIES: list[str] = ["staff", "services", "inventory", "sales", "appointments"]

# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
PERMISSIONS = [
    ("view_transaction", LazyString("View commission transactions", module_id="commissions")),
    ("add_transaction", LazyString("Add commission transactions", module_id="commissions")),
    ("approve_transaction", LazyString("Approve commission transactions", module_id="commissions")),
    ("view_rule", LazyString("View commission rules", module_id="commissions")),
    ("add_rule", LazyString("Add commission rules", module_id="commissions")),
    ("change_rule", LazyString("Edit commission rules", module_id="commissions")),
    ("delete_rule", LazyString("Delete commission rules", module_id="commissions")),
    ("view_payout", LazyString("View payouts", module_id="commissions")),
    ("add_payout", LazyString("Create payouts", module_id="commissions")),
    ("approve_payout", LazyString("Approve payouts", module_id="commissions")),
    ("process_payout", LazyString("Process payouts", module_id="commissions")),
    ("view_adjustment", LazyString("View adjustments", module_id="commissions")),
    ("add_adjustment", LazyString("Add adjustments", module_id="commissions")),
    ("delete_adjustment", LazyString("Delete adjustments", module_id="commissions")),
    ("manage_settings", LazyString("Manage commission settings", module_id="commissions")),
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
