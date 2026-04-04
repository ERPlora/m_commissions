"""
Commissions module hook registrations.

Registers actions and filters on the HookRegistry during module load.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.hooks.registry import HookRegistry

MODULE_ID = "commissions"


def register_hooks(hooks: HookRegistry, module_id: str) -> None:
    """
    Register hooks for the commissions module.

    Called by ModuleRuntime during module load.
    """
    # Action: after a payout is completed, notify other modules
    hooks.add_action(
        "commissions.payout_completed",
        _on_payout_completed,
        priority=10,
        module_id=module_id,
    )


async def _on_payout_completed(payout=None, **kwargs) -> None:
    """
    Hook triggered when a payout is marked as completed.
    Other modules can listen to this hook for integration purposes.
    """
