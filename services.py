"""
Commissions module services — ModuleService layer for AI assistant.

Replicates all AI tool functionality from ai_tools.py using the
ModuleService + @action pattern.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, UTC
from decimal import Decimal

from runtime.orm.transactions import atomic
from runtime.apps.service_facade import ModuleService, action

from commissions.models import CommissionRule, CommissionTransaction


class CommissionsService(ModuleService):
    """Commission rules, transactions, and summaries."""

    @action(permission="view_transaction")
    async def get_summary(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        staff_id: str = "",
    ) -> dict:
        """Get commission summary for a date range: total pending, approved, paid by staff."""
        d_from = date_from or str(date.today().replace(day=1))
        d_to = date_to or str(date.today())

        query = self.q(CommissionTransaction).filter(
            CommissionTransaction.transaction_date >= date.fromisoformat(d_from),
            CommissionTransaction.transaction_date <= date.fromisoformat(d_to),
        )
        if staff_id:
            query = query.filter(CommissionTransaction.staff_id == uuid.UUID(staff_id))

        all_trans = await query.all()

        by_status: dict[str, dict] = {}
        for t in all_trans:
            if t.status not in by_status:
                by_status[t.status] = {"total": Decimal("0"), "count": 0}
            by_status[t.status]["total"] += t.commission_amount
            by_status[t.status]["count"] += 1

        return {
            "date_from": d_from,
            "date_to": d_to,
            "by_status": [
                {"status": status, "total": str(data["total"]), "count": data["count"]}
                for status, data in by_status.items()
            ],
        }

    @action(permission="view_rule")
    async def list_rules(self) -> dict:
        """List active commission rules with type, rate, priority, and date range."""
        rules = await self.q(CommissionRule).filter(
            CommissionRule.is_active == True,  # noqa: E712
        ).order_by(CommissionRule.priority.desc()).all()

        return {
            "rules": [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "rule_type": r.rule_type,
                    "rate": str(r.rate) if r.rate else None,
                    "priority": r.priority,
                    "effective_from": str(r.effective_from) if r.effective_from else None,
                    "effective_until": str(r.effective_until) if r.effective_until else None,
                }
                for r in rules
            ],
        }

    @action(permission="add_rule", mutates=True)
    async def create_rule(
        self,
        *,
        name: str,
        rate: str,
        rule_type: str = "percentage",
        effective_from: str = "",
        effective_until: str = "",
        priority: int = 0,
    ) -> dict:
        """Create a commission rule (e.g., '10% on all sales')."""
        parsed_rate = Decimal(rate)
        if parsed_rate <= 0:
            return {"error": "Commission rate must be greater than 0."}

        if effective_from and effective_until:
            if date.fromisoformat(effective_from) >= date.fromisoformat(effective_until):
                return {"error": "effective_from must be before effective_until."}

        async with atomic(self.db) as session:
            rule = CommissionRule(
                hub_id=self.hub_id,
                name=name,
                rule_type=rule_type,
                rate=parsed_rate,
                effective_from=effective_from or None,
                effective_until=effective_until or None,
                priority=priority,
            )
            session.add(rule)
            await session.flush()

        return {"id": str(rule.id), "name": rule.name, "rate": str(rule.rate), "created": True}

    @action(permission="change_rule", mutates=True)
    async def update_rule(
        self,
        *,
        rule_id: str,
        name: str = "",
        rule_type: str = "",
        rate: str = "",
        effective_from: str = "",
        effective_until: str = "",
        priority: int | None = None,
        is_active: bool | None = None,
    ) -> dict:
        """Update a commission rule's name, rate, dates, or priority."""
        rule = await self.q(CommissionRule).get(uuid.UUID(rule_id))
        if rule is None:
            return {"error": "Commission rule not found"}

        if name:
            rule.name = name
        if rule_type:
            rule.rule_type = rule_type
        if rate:
            rule.rate = Decimal(rate)
        if effective_from:
            rule.effective_from = effective_from
        if effective_until:
            rule.effective_until = effective_until
        if priority is not None:
            rule.priority = priority
        if is_active is not None:
            rule.is_active = is_active

        await self.db.flush()
        return {"id": str(rule.id), "name": rule.name, "updated": True}

    @action(permission="delete_rule", mutates=True)
    async def delete_rule(self, *, rule_id: str) -> dict:
        """Soft-delete a commission rule (if no pending/approved transactions)."""
        rule = await self.q(CommissionRule).get(uuid.UUID(rule_id))
        if rule is None:
            return {"error": "Commission rule not found"}

        pending_count = await self.q(CommissionTransaction).filter(
            CommissionTransaction.rule_id == rule.id,
            CommissionTransaction.status.in_(["pending", "approved"]),
        ).count()
        if pending_count > 0:
            return {
                "error": (
                    f"Cannot delete rule '{rule.name}' — it has {pending_count} pending/approved "
                    f"transaction(s). Resolve or reassign them first."
                ),
            }

        name = rule.name
        rule.is_deleted = True
        rule.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return {"name": name, "deleted": True}
