"""
Pydantic schemas for commissions module.

Replaces Django forms — used for request validation and form rendering.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


# ============================================================================
# Commission Rule
# ============================================================================

class CommissionRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    rule_type: str = "percentage"
    rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    effective_from: date | None = None
    effective_until: date | None = None
    priority: int = Field(default=0, ge=0)
    is_active: bool = True


class CommissionRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    rule_type: str | None = None
    rate: Decimal | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    priority: int | None = None
    is_active: bool | None = None


# ============================================================================
# Commission Adjustment
# ============================================================================

class CommissionAdjustmentCreate(BaseModel):
    staff_id: uuid.UUID
    adjustment_type: str = "correction"
    amount: Decimal
    reason: str = Field(min_length=1)
    adjustment_date: date


# ============================================================================
# Payout
# ============================================================================

class PayoutCreate(BaseModel):
    staff_id: uuid.UUID
    period_start: date
    period_end: date
    notes: str = ""


class PayoutProcess(BaseModel):
    payment_method: str = ""
    payment_reference: str = ""


# ============================================================================
# Settings
# ============================================================================

class CommissionsSettingsUpdate(BaseModel):
    default_commission_rate: Decimal | None = Field(default=None, ge=0, le=100)
    calculation_basis: str | None = None
    payout_frequency: str | None = None
    payout_day: int | None = Field(default=None, ge=1, le=31)
    minimum_payout_amount: Decimal | None = Field(default=None, ge=0)
    apply_tax_withholding: bool | None = None
    tax_withholding_rate: Decimal | None = Field(default=None, ge=0, le=100)
    show_commission_on_receipt: bool | None = None
    show_pending_commission: bool | None = None


# ============================================================================
# API Calculate
# ============================================================================

class CalculateRequest(BaseModel):
    amount: Decimal
    rule_id: uuid.UUID


# ============================================================================
# Filters
# ============================================================================

class TransactionFilter(BaseModel):
    q: str = ""
    status: str = ""
    page: int = 1
    per_page: int = 20


class PayoutFilter(BaseModel):
    status: str = ""


class AdjustmentFilter(BaseModel):
    type: str = ""
