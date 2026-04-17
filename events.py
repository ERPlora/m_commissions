"""
Commissions module event subscriptions.

Registers handlers on the AsyncEventBus during module load.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.signals.dispatcher import AsyncEventBus

logger = logging.getLogger(__name__)

MODULE_ID = "commissions"


async def register_events(bus: AsyncEventBus, module_id: str) -> None:
    """
    Register event handlers for the commissions module.

    Called by ModuleRuntime during module load.
    """
    await bus.subscribe(
            "sales.completed",
            _on_sale_completed,
            module_id=module_id,
        )


async def _on_sale_completed(
    event: str,
    sender: object = None,
    sale: object = None,
    session: object = None,
    **kwargs: object,
) -> None:
    """
    When a sale completes, auto-generate commission transactions for the
    staff member(s) involved, based on matching commission rules.

    Requires a ``session`` kwarg (AsyncSession) passed by the event emitter
    so changes are persisted within the same transaction.
    """
    if sale is None or session is None:
        return

    hub_id = getattr(sale, "hub_id", None)
    if hub_id is None:
        return

    # Get the staff member from the sale
    staff_id = getattr(sale, "staff_id", None) or getattr(sale, "served_by_id", None)
    if staff_id is None:
        return

    try:
        from datetime import date as date_type
        from decimal import Decimal

        from runtime.models.queryset import HubQuery

        from .models import CommissionRule, CommissionTransaction, CommissionsSettings

        # Get settings
        settings_q = HubQuery(CommissionsSettings, session, hub_id)
        settings = await settings_q.first()
        if settings is None:
            return

        # Get applicable rules
        today = date_type.today()
        rules = await HubQuery(CommissionRule, session, hub_id).filter(
            CommissionRule.is_active == True,  # noqa: E712
        ).order_by(CommissionRule.priority.desc()).all()

        applicable_rules = [r for r in rules if r.is_applicable_on(today)]
        if not applicable_rules:
            return

        # Pick the best matching rule (highest priority)
        sale_total = getattr(sale, "total", Decimal("0"))
        if sale_total <= 0:
            return

        # Use the first applicable rule (highest priority due to ordering)
        rule = applicable_rules[0]
        commission_amount = rule.calculate_commission(sale_total)
        if commission_amount <= 0:
            return

        net, tax = settings.calculate_tax(commission_amount)

        # Get staff name
        staff_name = "Unknown"
        try:
            from staff.models import StaffMember
            member = await HubQuery(StaffMember, session, hub_id).get(staff_id)
            if member:
                staff_name = member.full_name
        except (ImportError, Exception):
            pass

        trans = CommissionTransaction(
            hub_id=hub_id,
            staff_id=staff_id,
            staff_name=staff_name,
            sale_id=sale.id,
            sale_reference=getattr(sale, "reference", ""),
            sale_amount=sale_total,
            commission_rate=rule.rate,
            commission_amount=commission_amount,
            tax_amount=tax,
            net_commission=net,
            rule_id=rule.id,
            status="pending",
            transaction_date=today,
        )
        session.add(trans)
        await session.flush()

        logger.info(
            "Created commission transaction %s for staff %s from sale %s",
            trans.id, staff_id, sale.id,
        )

    except Exception:
        logger.exception("Failed to create commission transaction for sale %s", getattr(sale, "id", "?"))
