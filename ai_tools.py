"""
AI tools for the Commissions module.

Uses @register_tool + AssistantTool class pattern.
All tools are async and use HubQuery for DB access.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, UTC
from decimal import Decimal
from typing import Any

from app.ai.registry import AssistantTool, register_tool
from app.core.db.query import HubQuery
from app.core.db.transactions import atomic

from .models import CommissionRule, CommissionTransaction


def _q(model, session, hub_id):
    return HubQuery(model, session, hub_id)


@register_tool
class GetCommissionSummary(AssistantTool):
    name = "get_commission_summary"
    description = (
        "Get commission summary for a date range: total pending, approved, paid by staff. "
        "Read-only — no side effects."
    )
    module_id = "commissions"
    required_permission = "commissions.view_transaction"
    parameters = {
        "type": "object",
        "properties": {
            "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD). Defaults to first of current month."},
            "date_to": {"type": "string", "description": "End date (YYYY-MM-DD). Defaults to today."},
            "staff_id": {"type": "string", "description": "Filter by staff member ID (UUID)."},
        },
        "required": [],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id
        date_from = args.get("date_from", str(date.today().replace(day=1)))
        date_to = args.get("date_to", str(date.today()))

        query = _q(CommissionTransaction, db, hub_id).filter(
            CommissionTransaction.transaction_date >= date.fromisoformat(date_from),
            CommissionTransaction.transaction_date <= date.fromisoformat(date_to),
        )
        if args.get("staff_id"):
            query = query.filter(CommissionTransaction.staff_id == uuid.UUID(args["staff_id"]))

        all_trans = await query.all()

        by_status: dict[str, dict] = {}
        for t in all_trans:
            if t.status not in by_status:
                by_status[t.status] = {"total": Decimal("0"), "count": 0}
            by_status[t.status]["total"] += t.commission_amount
            by_status[t.status]["count"] += 1

        return {
            "date_from": date_from,
            "date_to": date_to,
            "by_status": [
                {"status": status, "total": str(data["total"]), "count": data["count"]}
                for status, data in by_status.items()
            ],
        }


@register_tool
class ListCommissionRules(AssistantTool):
    name = "list_commission_rules"
    description = "List active commission rules with type, rate, priority, and date range."
    module_id = "commissions"
    required_permission = "commissions.view_rule"
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id
        rules = await _q(CommissionRule, db, hub_id).filter(
            CommissionRule.is_active == True,  # noqa: E712
        ).order_by(CommissionRule.priority.desc()).all()

        return {
            "rules": [{
                "id": str(r.id), "name": r.name,
                "rule_type": r.rule_type,
                "rate": str(r.rate) if r.rate else None,
                "priority": r.priority,
                "effective_from": str(r.effective_from) if r.effective_from else None,
                "effective_until": str(r.effective_until) if r.effective_until else None,
            } for r in rules],
        }


@register_tool
class CreateCommissionRule(AssistantTool):
    name = "create_commission_rule"
    description = (
        "Create a commission rule (e.g., '10% on all sales', '5% on services'). "
        "SIDE EFFECT: creates a new rule. Requires confirmation."
    )
    module_id = "commissions"
    required_permission = "commissions.add_rule"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Rule name (required)."},
            "rule_type": {"type": "string", "description": "Rule type: 'flat', 'percentage', or 'tiered'. Default: 'percentage'."},
            "rate": {"type": "string", "description": "Commission rate percentage or flat amount (required)."},
            "effective_from": {"type": "string", "description": "Start date (YYYY-MM-DD). Optional."},
            "effective_until": {"type": "string", "description": "End date (YYYY-MM-DD). Optional."},
            "priority": {"type": "integer", "description": "Priority order (higher = applied first). Default: 0."},
        },
        "required": ["name", "rate"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id

        # Validate rate > 0
        rate = Decimal(args["rate"])
        if rate <= 0:
            return {"error": "Commission rate must be greater than 0."}

        # Validate effective_from < effective_until if both provided
        effective_from = args.get("effective_from")
        effective_until = args.get("effective_until")
        if effective_from and effective_until:
            if date.fromisoformat(effective_from) >= date.fromisoformat(effective_until):
                return {"error": "effective_from must be before effective_until."}

        async with atomic(db) as session:
            rule = CommissionRule(
                hub_id=hub_id,
                name=args["name"],
                rule_type=args.get("rule_type", "percentage"),
                rate=rate,
                effective_from=effective_from,
                effective_until=effective_until,
                priority=args.get("priority", 0),
            )
            session.add(rule)
            await session.flush()

        return {"id": str(rule.id), "name": rule.name, "rate": str(rule.rate), "created": True}


@register_tool
class UpdateCommissionRule(AssistantTool):
    name = "update_commission_rule"
    description = (
        "Update a commission rule's name, rate, dates, or priority. "
        "SIDE EFFECT: modifies the rule. Requires confirmation."
    )
    module_id = "commissions"
    required_permission = "commissions.change_rule"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "rule_id": {"type": "string", "description": "Commission rule ID (UUID). Required."},
            "name": {"type": "string"},
            "rule_type": {"type": "string", "description": "flat, percentage, tiered"},
            "rate": {"type": "string", "description": "Commission rate"},
            "effective_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
            "effective_until": {"type": "string", "description": "End date (YYYY-MM-DD)"},
            "priority": {"type": "integer"},
            "is_active": {"type": "boolean"},
        },
        "required": ["rule_id"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id
        rule = await _q(CommissionRule, db, hub_id).get(uuid.UUID(args["rule_id"]))
        if rule is None:
            return {"error": "Commission rule not found"}

        for field in ("name", "rule_type", "effective_from", "effective_until", "priority", "is_active"):
            if args.get(field) is not None:
                setattr(rule, field, args[field])
        if args.get("rate") is not None:
            rule.rate = Decimal(args["rate"])
        await db.flush()

        return {"id": str(rule.id), "name": rule.name, "updated": True}


@register_tool
class DeleteCommissionRule(AssistantTool):
    name = "delete_commission_rule"
    description = (
        "Delete a commission rule. "
        "SIDE EFFECT: soft-deletes the rule. Requires confirmation."
    )
    module_id = "commissions"
    required_permission = "commissions.delete_rule"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "rule_id": {"type": "string", "description": "Commission rule ID (UUID). Required."},
        },
        "required": ["rule_id"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict, request: Any) -> dict:
        db = request.state.db
        hub_id = request.state.hub_id
        rule = await _q(CommissionRule, db, hub_id).get(uuid.UUID(args["rule_id"]))
        if rule is None:
            return {"error": "Commission rule not found"}

        # Check for pending/approved transactions using this rule
        pending_count = await _q(CommissionTransaction, db, hub_id).filter(
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
        await db.flush()
        return {"name": name, "deleted": True}
