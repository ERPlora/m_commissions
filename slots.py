"""
Commissions module slot registrations.

No POS slots needed for commissions — this module is admin-only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.slots import SlotRegistry

MODULE_ID = "commissions"


def register_slots(slots: SlotRegistry, module_id: str) -> None:
    """
    Register slot content for the commissions module.

    Called by ModuleRuntime during module load.
    """
    # No POS slots — commissions is a back-office module
