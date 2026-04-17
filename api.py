"""
Commissions module REST API — FastAPI router.

JSON endpoints for external consumers (Cloud sync, CLI, webhooks).
Mounted at /api/v1/m/commissions/ by ModuleRuntime.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from runtime.models.queryset import HubQuery
from runtime.auth.current_user import DbSession, HubId

from .models import (
    CommissionPayout,
    CommissionRule,
    CommissionTransaction,
)

api_router = APIRouter()


def _q(model, session, hub_id):
    return HubQuery(model, session, hub_id)


@api_router.get("/rules")
async def list_rules(
    request: Request, db: DbSession, hub_id: HubId,
    active_only: bool = True,
):
    """List commission rules."""
    query = _q(CommissionRule, db, hub_id)
    if active_only:
        query = query.filter(CommissionRule.is_active == True)  # noqa: E712
    rules = await query.order_by(CommissionRule.priority.desc(), CommissionRule.name).all()
    return {
        "rules": [{
            "id": str(r.id), "name": r.name,
            "rule_type": r.rule_type, "rate": str(r.rate),
            "priority": r.priority, "is_active": r.is_active,
            "effective_from": str(r.effective_from) if r.effective_from else None,
            "effective_until": str(r.effective_until) if r.effective_until else None,
        } for r in rules],
    }


@api_router.get("/rules/{rule_id}")
async def get_rule(
    rule_id: uuid.UUID, request: Request, db: DbSession, hub_id: HubId,
):
    """Get a single commission rule."""
    rule = await _q(CommissionRule, db, hub_id).get(rule_id)
    if rule is None:
        return JSONResponse({"error": "Rule not found"}, status_code=404)
    return {
        "id": str(rule.id), "name": rule.name, "description": rule.description,
        "rule_type": rule.rule_type, "rate": str(rule.rate),
        "tier_thresholds": rule.tier_thresholds,
        "priority": rule.priority, "is_active": rule.is_active,
        "effective_from": str(rule.effective_from) if rule.effective_from else None,
        "effective_until": str(rule.effective_until) if rule.effective_until else None,
        "created_at": rule.created_at.isoformat(),
    }


@api_router.get("/transactions")
async def list_transactions(
    request: Request, db: DbSession, hub_id: HubId,
    status: str = "", staff_id: str = "",
    start_date: str = "", end_date: str = "",
    offset: int = 0, limit: int = Query(default=20, le=100),
):
    """List commission transactions."""
    query = _q(CommissionTransaction, db, hub_id)
    if status:
        query = query.filter(CommissionTransaction.status == status)
    if staff_id:
        query = query.filter(CommissionTransaction.staff_id == uuid.UUID(staff_id))
    if start_date:
        query = query.filter(CommissionTransaction.transaction_date >= date.fromisoformat(start_date))
    if end_date:
        query = query.filter(CommissionTransaction.transaction_date <= date.fromisoformat(end_date))

    total = await query.count()
    transactions = await query.order_by(
        CommissionTransaction.transaction_date.desc(),
    ).offset(offset).limit(limit).all()

    return {
        "transactions": [{
            "id": str(t.id), "staff_name": t.staff_name,
            "sale_amount": str(t.sale_amount), "commission_rate": str(t.commission_rate),
            "commission_amount": str(t.commission_amount),
            "net_commission": str(t.net_commission), "tax_amount": str(t.tax_amount),
            "status": t.status, "transaction_date": str(t.transaction_date),
            "sale_reference": t.sale_reference,
        } for t in transactions],
        "total": total,
    }


@api_router.get("/payouts")
async def list_payouts(
    request: Request, db: DbSession, hub_id: HubId,
    status: str = "",
    offset: int = 0, limit: int = Query(default=20, le=100),
):
    """List payouts."""
    query = _q(CommissionPayout, db, hub_id)
    if status:
        query = query.filter(CommissionPayout.status == status)

    total = await query.count()
    payouts = await query.order_by(CommissionPayout.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "payouts": [{
            "id": str(p.id), "reference": p.reference, "staff_name": p.staff_name,
            "period_start": str(p.period_start), "period_end": str(p.period_end),
            "gross_amount": str(p.gross_amount), "net_amount": str(p.net_amount),
            "tax_amount": str(p.tax_amount),
            "transaction_count": p.transaction_count, "status": p.status,
            "payment_method": p.payment_method,
        } for p in payouts],
        "total": total,
    }


@api_router.get("/summary")
async def commission_summary(
    request: Request, db: DbSession, hub_id: HubId,
    start_date: str = "", end_date: str = "",
    staff_id: str = "",
):
    """Get commission summary with totals grouped by status."""
    query = _q(CommissionTransaction, db, hub_id)
    if start_date:
        query = query.filter(CommissionTransaction.transaction_date >= date.fromisoformat(start_date))
    if end_date:
        query = query.filter(CommissionTransaction.transaction_date <= date.fromisoformat(end_date))
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
        "start_date": start_date or str(date.today().replace(day=1)),
        "end_date": end_date or str(date.today()),
        "by_status": [
            {"status": status, "total": str(data["total"]), "count": data["count"]}
            for status, data in by_status.items()
        ],
    }
