"""
Commissions module HTMX views — FastAPI router.

Replaces Django views.py + urls.py. Uses @htmx_view decorator
(partial for HTMX requests, full page for direct navigation).
Mounted at /m/commissions/ by ModuleRuntime.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, UTC
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import selectinload

from app.core.db.query import HubQuery
from app.core.db.transactions import atomic
from app.core.dependencies import CurrentUser, DbSession, HubId
from app.core.htmx import htmx_view

from .models import (
    CommissionsSettings,
    CommissionRule,
    CommissionTransaction,
    CommissionPayout,
    CommissionAdjustment,
    TRANSACTION_STATUS_CHOICES,
    PAYOUT_STATUS_CHOICES,
    ADJUSTMENT_TYPE_CHOICES,
    RULE_TYPE_CHOICES,
    CALCULATION_BASIS_CHOICES,
    PAYOUT_FREQUENCY_CHOICES,
    PAYMENT_METHOD_CHOICES,
)

router = APIRouter()


def _q(model, db, hub_id):
    return HubQuery(model, db, hub_id)


async def _get_settings(db, hub_id) -> CommissionsSettings:
    """Get or create commissions settings for the hub."""
    q = _q(CommissionsSettings, db, hub_id)
    settings = await q.first()
    if settings is None:
        settings = CommissionsSettings(hub_id=hub_id)
        db.add(settings)
        await db.flush()
    return settings


# ============================================================================
# Dashboard
# ============================================================================

@router.get("/")
@router.get("/dashboard")
@htmx_view(module_id="commissions", view_id="dashboard")
async def dashboard(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Commission dashboard with stats, top earners, recent transactions."""
    today = date.today()
    month_start = today.replace(day=1)

    # Monthly stats
    trans_q = _q(CommissionTransaction, db, hub_id).filter(
        CommissionTransaction.transaction_date >= month_start,
        CommissionTransaction.transaction_date <= today,
    )
    all_trans = await trans_q.all()

    total_commission = sum(t.commission_amount for t in all_trans) if all_trans else Decimal("0")
    total_net = sum(t.net_commission for t in all_trans) if all_trans else Decimal("0")
    total_tax = sum(t.tax_amount for t in all_trans) if all_trans else Decimal("0")
    transaction_count = len(all_trans)

    pending_count = await _q(CommissionTransaction, db, hub_id).filter(
        CommissionTransaction.status == "pending",
    ).count()

    stats = {
        "total_commission": total_commission,
        "total_net": total_net,
        "total_tax": total_tax,
        "transaction_count": transaction_count,
        "pending_transactions": pending_count,
    }

    # Top earners
    approved_trans = [t for t in all_trans if t.status in ("approved", "paid")]
    earner_map: dict[str, dict] = {}
    for t in approved_trans:
        key = str(t.staff_id) if t.staff_id else t.staff_name
        if key not in earner_map:
            earner_map[key] = {"staff_name": t.staff_name, "total": Decimal("0")}
        earner_map[key]["total"] += t.net_commission
    top_earners = sorted(earner_map.values(), key=lambda x: x["total"], reverse=True)[:5]

    # Recent transactions
    recent_transactions = await _q(CommissionTransaction, db, hub_id).options(
        selectinload(CommissionTransaction.rule),
    ).order_by(
        CommissionTransaction.transaction_date.desc(),
        CommissionTransaction.created_at.desc(),
    ).limit(10).all()

    # Pending payouts
    pending_payouts = await _q(CommissionPayout, db, hub_id).filter(
        CommissionPayout.status == "pending",
    ).order_by(CommissionPayout.created_at.desc()).limit(5).all()

    return {
        "stats": stats,
        "top_earners": top_earners,
        "recent_transactions": recent_transactions,
        "pending_payouts": pending_payouts,
    }


# ============================================================================
# Transactions
# ============================================================================

@router.get("/transactions")
@htmx_view(module_id="commissions", view_id="transactions")
async def transaction_list(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
    status: str = "", q: str = "",
):
    """Transaction list with search and status filter."""
    query = _q(CommissionTransaction, db, hub_id).options(
        selectinload(CommissionTransaction.rule),
    )

    if status:
        query = query.filter(CommissionTransaction.status == status)

    if q:
        from sqlalchemy import or_
        query = query.filter(or_(
            CommissionTransaction.staff_name.ilike(f"%{q}%"),
            CommissionTransaction.sale_reference.ilike(f"%{q}%"),
            CommissionTransaction.description.ilike(f"%{q}%"),
        ))

    transactions = await query.order_by(
        CommissionTransaction.transaction_date.desc(),
        CommissionTransaction.created_at.desc(),
    ).all()

    return {
        "transactions": transactions,
        "status_filter": status,
        "search": q,
        "status_choices": TRANSACTION_STATUS_CHOICES,
    }


@router.get("/transactions/{pk}")
@htmx_view(module_id="commissions", view_id="transactions")
async def transaction_detail(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Transaction detail view."""
    trans = await _q(CommissionTransaction, db, hub_id).options(
        selectinload(CommissionTransaction.rule),
        selectinload(CommissionTransaction.payout),
    ).get(pk)
    if trans is None:
        return JSONResponse({"error": "Transaction not found"}, status_code=404)

    return {"transaction": trans}


@router.post("/transactions/{pk}/approve")
async def transaction_approve(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Approve a pending transaction."""
    trans = await _q(CommissionTransaction, db, hub_id).get(pk)
    if trans is None:
        return JSONResponse({"error": "Transaction not found"}, status_code=404)

    if trans.status != "pending":
        return JSONResponse(
            {"success": False, "error": f"Transaction is {trans.status}, cannot approve"},
            status_code=400,
        )

    trans.status = "approved"
    trans.approved_by_id = user.id
    trans.approved_at = datetime.now(UTC)
    await db.flush()
    return JSONResponse({"success": True})


@router.post("/transactions/{pk}/reject")
async def transaction_reject(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Reject a pending transaction."""
    trans = await _q(CommissionTransaction, db, hub_id).get(pk)
    if trans is None:
        return JSONResponse({"error": "Transaction not found"}, status_code=404)

    if trans.status != "pending":
        return JSONResponse(
            {"success": False, "error": f"Transaction is {trans.status}, cannot reject"},
            status_code=400,
        )

    form = await request.form()
    reason = form.get("reason", "")
    trans.status = "cancelled"
    if reason:
        trans.notes = f"{trans.notes}\nRejection: {reason}".strip()
    await db.flush()
    return JSONResponse({"success": True})


# ============================================================================
# Payouts
# ============================================================================

@router.get("/payouts")
@htmx_view(module_id="commissions", view_id="payouts")
async def payout_list(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
    status: str = "",
):
    """Payout list with status filter."""
    query = _q(CommissionPayout, db, hub_id)

    if status:
        query = query.filter(CommissionPayout.status == status)

    payouts = await query.order_by(CommissionPayout.created_at.desc()).all()

    return {
        "payouts": payouts,
        "status_filter": status,
        "status_choices": PAYOUT_STATUS_CHOICES,
    }


@router.post("/payouts/create")
async def payout_create(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Create a payout batch for a staff member's approved transactions."""
    form = await request.form()
    staff_pk = form.get("staff_id", "")
    period_start_str = form.get("period_start", "")
    period_end_str = form.get("period_end", "")
    notes = form.get("notes", "")

    try:
        staff_uuid = uuid.UUID(staff_pk)
        p_start = date.fromisoformat(period_start_str)
        p_end = date.fromisoformat(period_end_str)
    except (ValueError, TypeError) as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

    try:
        # Get staff member name
        from staff.models import StaffMember
        member = await _q(StaffMember, db, hub_id).get(staff_uuid)
        if member is None:
            return JSONResponse({"success": False, "error": "Staff member not found"}, status_code=400)

        async with atomic(db) as session:
            # Find approved transactions not yet in a payout
            transactions = await _q(CommissionTransaction, session, hub_id).filter(
                CommissionTransaction.staff_id == staff_uuid,
                CommissionTransaction.status == "approved",
                CommissionTransaction.payout_id == None,  # noqa: E711
                CommissionTransaction.transaction_date >= p_start,
                CommissionTransaction.transaction_date <= p_end,
            ).all()

            if not transactions:
                return JSONResponse(
                    {"success": False, "error": "No approved transactions for this period"},
                    status_code=400,
                )

            gross = sum(t.commission_amount for t in transactions)
            tax = sum(t.tax_amount for t in transactions)
            count = len(transactions)

            settings = await _get_settings(session, hub_id)
            if settings.minimum_payout_amount > 0 and gross < settings.minimum_payout_amount:
                return JSONResponse(
                    {"success": False, "error": f"Amount {gross} below minimum {settings.minimum_payout_amount}"},
                    status_code=400,
                )

            # Generate reference
            prefix = f"PAY-{date.today().strftime('%Y%m')}-"
            existing_count = await _q(CommissionPayout, session, hub_id).filter(
                CommissionPayout.reference.startswith(prefix),
            ).count()
            reference = f"{prefix}{existing_count + 1:04d}"

            payout = CommissionPayout(
                hub_id=hub_id,
                reference=reference,
                staff_id=staff_uuid,
                staff_name=member.full_name,
                period_start=p_start,
                period_end=p_end,
                gross_amount=gross,
                tax_amount=tax,
                net_amount=gross - tax,
                transaction_count=count,
                notes=notes,
                status="pending",
            )
            session.add(payout)
            await session.flush()

            for t in transactions:
                t.payout_id = payout.id

        return JSONResponse({"success": True, "id": str(payout.id)})

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.get("/payouts/{pk}")
@htmx_view(module_id="commissions", view_id="payouts")
async def payout_detail(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Payout detail with transactions and adjustments."""
    payout = await _q(CommissionPayout, db, hub_id).get(pk)
    if payout is None:
        return JSONResponse({"error": "Payout not found"}, status_code=404)

    transactions = await _q(CommissionTransaction, db, hub_id).filter(
        CommissionTransaction.payout_id == pk,
    ).options(selectinload(CommissionTransaction.rule)).all()

    adjustments = await _q(CommissionAdjustment, db, hub_id).filter(
        CommissionAdjustment.payout_id == pk,
    ).all()

    return {
        "payout": payout,
        "transactions": transactions,
        "adjustments": adjustments,
        "payment_method_choices": PAYMENT_METHOD_CHOICES,
    }


@router.post("/payouts/{pk}/approve")
async def payout_approve(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Approve a pending payout."""
    payout = await _q(CommissionPayout, db, hub_id).get(pk)
    if payout is None:
        return JSONResponse({"error": "Payout not found"}, status_code=404)

    if payout.status not in ("draft", "pending"):
        return JSONResponse(
            {"success": False, "error": f"Payout is {payout.status}, cannot approve"},
            status_code=400,
        )

    payout.status = "approved"
    payout.approved_by_id = user.id
    payout.approved_at = datetime.now(UTC)
    await db.flush()
    return JSONResponse({"success": True})


@router.post("/payouts/{pk}/process")
async def payout_process(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Process an approved payout (mark as paid)."""
    payout = await _q(CommissionPayout, db, hub_id).get(pk)
    if payout is None:
        return JSONResponse({"error": "Payout not found"}, status_code=404)

    if payout.status not in ("pending", "approved"):
        return JSONResponse(
            {"success": False, "error": f"Payout is {payout.status}, cannot process"},
            status_code=400,
        )

    form = await request.form()
    payment_method = form.get("payment_method", "")
    payment_reference = form.get("payment_reference", "")

    payout.status = "completed"
    payout.payment_method = payment_method
    payout.payment_reference = payment_reference
    payout.paid_by_id = user.id
    payout.paid_at = datetime.now(UTC)
    await db.flush()

    # Mark all linked transactions as paid
    transactions = await _q(CommissionTransaction, db, hub_id).filter(
        CommissionTransaction.payout_id == pk,
    ).all()
    for t in transactions:
        t.status = "paid"
    await db.flush()

    return JSONResponse({"success": True})


@router.post("/payouts/{pk}/cancel")
async def payout_cancel(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Cancel a payout and unlink transactions."""
    payout = await _q(CommissionPayout, db, hub_id).get(pk)
    if payout is None:
        return JSONResponse({"error": "Payout not found"}, status_code=404)

    if payout.status == "completed":
        return JSONResponse(
            {"success": False, "error": "Cannot cancel a completed payout"},
            status_code=400,
        )

    form = await request.form()
    reason = form.get("reason", "")

    async with atomic(db) as session:
        # Unlink transactions
        transactions = await _q(CommissionTransaction, session, hub_id).filter(
            CommissionTransaction.payout_id == pk,
        ).all()
        for t in transactions:
            t.payout_id = None
            t.status = "approved"

        payout.status = "cancelled"
        if reason:
            payout.notes = f"{payout.notes}\nCancellation: {reason}".strip()

    return JSONResponse({"success": True})


# ============================================================================
# Rules
# ============================================================================

@router.get("/rules")
@htmx_view(module_id="commissions", view_id="rules")
async def rule_list(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """List all commission rules."""
    rules = await _q(CommissionRule, db, hub_id).order_by(
        CommissionRule.priority.desc(), CommissionRule.name,
    ).all()

    return {
        "rules": rules,
        "rule_type_choices": RULE_TYPE_CHOICES,
    }


@router.post("/rules/add")
async def rule_add(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Create a new commission rule."""
    form = await request.form()
    try:
        name = form.get("name", "").strip()
        if not name:
            return JSONResponse({"success": False, "error": "Name is required"}, status_code=400)

        async with atomic(db) as session:
            rule = CommissionRule(
                hub_id=hub_id,
                name=name,
                description=form.get("description", ""),
                rule_type=form.get("rule_type", "percentage"),
                rate=Decimal(form.get("rate", "0")),
                priority=int(form.get("priority", "0")),
                is_active=form.get("is_active", "true") in ("true", "on", "1"),
            )
            session.add(rule)
            await session.flush()

        return JSONResponse({"success": True, "id": str(rule.id)})

    except (ValueError, InvalidOperation) as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.get("/rules/{pk}")
@htmx_view(module_id="commissions", view_id="rules")
async def rule_detail(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Rule detail view."""
    rule = await _q(CommissionRule, db, hub_id).get(pk)
    if rule is None:
        return JSONResponse({"error": "Rule not found"}, status_code=404)

    transaction_count = await _q(CommissionTransaction, db, hub_id).filter(
        CommissionTransaction.rule_id == pk,
    ).count()

    return {"rule": rule, "transaction_count": transaction_count}


@router.post("/rules/{pk}/edit")
async def rule_edit(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Update a commission rule."""
    rule = await _q(CommissionRule, db, hub_id).get(pk)
    if rule is None:
        return JSONResponse({"error": "Rule not found"}, status_code=404)

    form = await request.form()
    for field_name in ("name", "description", "rule_type"):
        value = form.get(field_name)
        if value is not None:
            setattr(rule, field_name, value)

    rate = form.get("rate")
    if rate is not None:
        rule.rate = Decimal(rate)

    priority = form.get("priority")
    if priority is not None:
        rule.priority = int(priority)

    is_active = form.get("is_active")
    if is_active is not None:
        rule.is_active = is_active in ("true", "on", "1")

    await db.flush()
    return JSONResponse({"success": True})


@router.post("/rules/{pk}/delete")
async def rule_delete(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Soft-delete a commission rule."""
    rule = await _q(CommissionRule, db, hub_id).get(pk)
    if rule is None:
        return JSONResponse({"error": "Rule not found"}, status_code=404)

    # Check if used in transactions
    trans_count = await _q(CommissionTransaction, db, hub_id).filter(
        CommissionTransaction.rule_id == pk,
    ).count()
    if trans_count > 0:
        return JSONResponse(
            {"success": False, "error": "Cannot delete rule with existing transactions"},
            status_code=400,
        )

    rule.is_deleted = True
    rule.deleted_at = datetime.now(UTC)
    await db.flush()
    return JSONResponse({"success": True})


@router.post("/rules/{pk}/toggle")
async def rule_toggle(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Toggle a rule's active status."""
    rule = await _q(CommissionRule, db, hub_id).get(pk)
    if rule is None:
        return JSONResponse({"error": "Rule not found"}, status_code=404)

    rule.is_active = not rule.is_active
    await db.flush()
    return JSONResponse({"success": True, "is_active": rule.is_active})


# ============================================================================
# Adjustments
# ============================================================================

@router.get("/adjustments")
@htmx_view(module_id="commissions", view_id="adjustments")
async def adjustment_list(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
    type: str = "",
):
    """List all commission adjustments."""
    query = _q(CommissionAdjustment, db, hub_id)

    if type:
        query = query.filter(CommissionAdjustment.adjustment_type == type)

    adjustments = await query.order_by(
        CommissionAdjustment.adjustment_date.desc(),
        CommissionAdjustment.created_at.desc(),
    ).all()

    return {
        "adjustments": adjustments,
        "type_filter": type,
        "type_choices": ADJUSTMENT_TYPE_CHOICES,
    }


@router.post("/adjustments/add")
async def adjustment_add(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Create a new adjustment."""
    form = await request.form()
    staff_pk = form.get("staff_id", "")
    adj_type = form.get("adjustment_type", "correction")
    amount_str = form.get("amount", "0")
    reason = form.get("reason", "").strip()
    adj_date_str = form.get("adjustment_date", "")

    if not reason:
        return JSONResponse({"success": False, "error": "Reason is required"}, status_code=400)

    try:
        staff_uuid = uuid.UUID(staff_pk)
        amount = Decimal(amount_str)
        adj_date = date.fromisoformat(adj_date_str) if adj_date_str else date.today()
    except (ValueError, InvalidOperation) as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

    # Get staff name
    staff_name = "Unknown"
    try:
        from staff.models import StaffMember
        member = await _q(StaffMember, db, hub_id).get(staff_uuid)
        if member:
            staff_name = member.full_name
    except (ImportError, Exception):
        pass

    async with atomic(db) as session:
        adj = CommissionAdjustment(
            hub_id=hub_id,
            staff_id=staff_uuid,
            staff_name=staff_name,
            adjustment_type=adj_type,
            amount=amount,
            reason=reason,
            adjustment_date=adj_date,
            created_by_id=user.id,
        )
        session.add(adj)
        await session.flush()

    return JSONResponse({"success": True, "id": str(adj.id)})


@router.get("/adjustments/{pk}")
@htmx_view(module_id="commissions", view_id="adjustments")
async def adjustment_detail(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Adjustment detail view."""
    adj = await _q(CommissionAdjustment, db, hub_id).options(
        selectinload(CommissionAdjustment.payout),
    ).get(pk)
    if adj is None:
        return JSONResponse({"error": "Adjustment not found"}, status_code=404)

    return {"adjustment": adj}


@router.post("/adjustments/{pk}/delete")
async def adjustment_delete(
    request: Request, pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Soft-delete an adjustment."""
    adj = await _q(CommissionAdjustment, db, hub_id).get(pk)
    if adj is None:
        return JSONResponse({"error": "Adjustment not found"}, status_code=404)

    if adj.payout_id:
        return JSONResponse(
            {"success": False, "error": "Cannot delete adjustment linked to a payout"},
            status_code=400,
        )

    adj.is_deleted = True
    adj.deleted_at = datetime.now(UTC)
    await db.flush()
    return JSONResponse({"success": True})


# ============================================================================
# Settings
# ============================================================================

@router.get("/settings")
@htmx_view(module_id="commissions", view_id="settings")
async def settings_view(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Commission settings page."""
    settings = await _get_settings(db, hub_id)

    return {
        "settings": settings,
        "calculation_basis_choices": CALCULATION_BASIS_CHOICES,
        "payout_frequency_choices": PAYOUT_FREQUENCY_CHOICES,
    }


@router.post("/settings/save")
async def settings_save(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Save settings (form post)."""
    settings = await _get_settings(db, hub_id)
    form = await request.form()

    for field_name in (
        "default_commission_rate", "calculation_basis",
        "payout_frequency", "payout_day", "minimum_payout_amount",
        "apply_tax_withholding", "tax_withholding_rate",
        "show_commission_on_receipt", "show_pending_commission",
    ):
        value = form.get(field_name)
        if value is not None:
            if field_name in ("default_commission_rate", "minimum_payout_amount", "tax_withholding_rate"):
                setattr(settings, field_name, Decimal(value))
            elif field_name == "payout_day":
                setattr(settings, field_name, int(value))
            elif field_name in ("apply_tax_withholding", "show_commission_on_receipt", "show_pending_commission"):
                setattr(settings, field_name, value in ("true", "on", "1"))
            else:
                setattr(settings, field_name, value)

    await db.flush()
    return JSONResponse({"success": True})


@router.post("/settings/toggle")
async def settings_toggle(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Toggle a boolean settings field."""
    settings = await _get_settings(db, hub_id)
    form = await request.form()
    field = form.get("field", "")

    toggleable = ("apply_tax_withholding", "show_commission_on_receipt", "show_pending_commission")
    if field not in toggleable:
        return JSONResponse({"success": False, "error": "Invalid field"}, status_code=400)

    setattr(settings, field, not getattr(settings, field))
    await db.flush()
    return JSONResponse({"success": True, "value": getattr(settings, field)})


@router.post("/settings/input")
async def settings_input(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Update a single input settings field."""
    settings = await _get_settings(db, hub_id)
    form = await request.form()
    field = form.get("field", "")
    value = form.get("value", "")

    input_fields = {
        "default_commission_rate": lambda v: Decimal(v),
        "payout_day": int,
        "minimum_payout_amount": lambda v: Decimal(v),
        "tax_withholding_rate": lambda v: Decimal(v),
    }

    if field not in input_fields:
        return JSONResponse({"success": False, "error": "Invalid field"}, status_code=400)

    try:
        parsed = input_fields[field](value)
        setattr(settings, field, parsed)
        await db.flush()
        return JSONResponse({"success": True})
    except (ValueError, TypeError, InvalidOperation) as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.post("/settings/reset")
async def settings_reset(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Reset all settings to defaults."""
    settings = await _get_settings(db, hub_id)
    settings.default_commission_rate = Decimal("10.00")
    settings.calculation_basis = "net"
    settings.payout_frequency = "monthly"
    settings.payout_day = 1
    settings.minimum_payout_amount = Decimal("0.00")
    settings.apply_tax_withholding = False
    settings.tax_withholding_rate = Decimal("0.00")
    settings.show_commission_on_receipt = False
    settings.show_pending_commission = True
    await db.flush()
    return JSONResponse({"success": True})


# ============================================================================
# API Endpoints (in-module, for AJAX calls)
# ============================================================================

@router.post("/api/calculate")
async def api_calculate(
    request: Request, db: DbSession, user: CurrentUser, hub_id: HubId,
):
    """Calculate commission for given amount and rule."""
    form = await request.form()
    try:
        amount = Decimal(form.get("amount", "0"))
        rule_pk = form.get("rule_id")

        if not rule_pk:
            return JSONResponse({"error": "Rule ID required"}, status_code=400)

        rule = await _q(CommissionRule, db, hub_id).get(uuid.UUID(rule_pk))
        if rule is None:
            return JSONResponse({"error": "Rule not found"}, status_code=404)

        commission = rule.calculate_commission(amount)
        settings = await _get_settings(db, hub_id)
        net, tax = settings.calculate_tax(commission)

        return JSONResponse({
            "amount": str(amount),
            "commission_amount": str(commission),
            "tax_withheld": str(tax),
            "net_amount": str(net),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/api/staff/{staff_pk}/summary")
async def api_staff_summary(
    request: Request, staff_pk: uuid.UUID,
    db: DbSession, user: CurrentUser, hub_id: HubId,
    start_date: str = "", end_date: str = "",
):
    """Get commission summary for a staff member."""
    try:
        query = _q(CommissionTransaction, db, hub_id).filter(
            CommissionTransaction.staff_id == staff_pk,
        )
        if start_date:
            query = query.filter(
                CommissionTransaction.transaction_date >= date.fromisoformat(start_date),
            )
        if end_date:
            query = query.filter(
                CommissionTransaction.transaction_date <= date.fromisoformat(end_date),
            )

        all_trans = await query.all()

        total_sales = sum(t.sale_amount for t in all_trans) if all_trans else Decimal("0")
        total_commission = sum(t.commission_amount for t in all_trans) if all_trans else Decimal("0")
        total_net = sum(t.net_commission for t in all_trans) if all_trans else Decimal("0")
        total_tax = sum(t.tax_amount for t in all_trans) if all_trans else Decimal("0")

        pending_trans = [t for t in all_trans if t.status == "pending"]
        paid_trans = [t for t in all_trans if t.status == "paid"]

        return JSONResponse({
            "total_sales": str(total_sales),
            "total_commission": str(total_commission),
            "total_net": str(total_net),
            "total_tax": str(total_tax),
            "transaction_count": len(all_trans),
            "pending_amount": str(sum(t.net_commission for t in pending_trans)),
            "pending_count": len(pending_trans),
            "paid_amount": str(sum(t.net_commission for t in paid_trans)),
            "paid_count": len(paid_trans),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
