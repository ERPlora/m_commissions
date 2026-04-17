"""
Commissions module models — SQLAlchemy 2.0.

Models: CommissionsSettings, CommissionRule, CommissionTransaction,
        CommissionPayout, CommissionAdjustment.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from runtime.models.base import HubBaseModel

if TYPE_CHECKING:
    pass


# ============================================================================
# Choices (for templates / display helpers)
# ============================================================================

CALCULATION_BASIS_CHOICES = {
    "gross": "Gross Sales",
    "net": "Net Sales (after discounts)",
    "profit": "Profit Margin",
}

PAYOUT_FREQUENCY_CHOICES = {
    "weekly": "Weekly",
    "biweekly": "Bi-weekly",
    "monthly": "Monthly",
    "custom": "Custom",
}

RULE_TYPE_CHOICES = {
    "flat": "Flat Amount",
    "percentage": "Percentage",
    "tiered": "Tiered (based on sales volume)",
}

TRANSACTION_STATUS_CHOICES = {
    "pending": "Pending",
    "approved": "Approved",
    "paid": "Paid",
    "cancelled": "Cancelled",
    "adjusted": "Adjusted",
}

PAYOUT_STATUS_CHOICES = {
    "draft": "Draft",
    "pending": "Pending Approval",
    "approved": "Approved",
    "processing": "Processing",
    "completed": "Completed",
    "failed": "Failed",
    "cancelled": "Cancelled",
    "included_in_payslip": "Included in Payslip",
}

PAYMENT_METHOD_CHOICES = {
    "cash": "Cash",
    "bank_transfer": "Bank Transfer",
    "check": "Check",
    "payroll": "Added to Payroll",
    "other": "Other",
}

ADJUSTMENT_TYPE_CHOICES = {
    "bonus": "Bonus",
    "correction": "Correction",
    "deduction": "Deduction",
    "refund_adjustment": "Refund Adjustment",
    "other": "Other",
}

# Status → badge color mapping (for templates)
TRANSACTION_STATUS_COLORS = {
    "pending": "warning",
    "approved": "success",
    "paid": "primary",
    "cancelled": "error",
    "adjusted": "medium",
}

PAYOUT_STATUS_COLORS = {
    "draft": "medium",
    "pending": "warning",
    "approved": "primary",
    "processing": "primary",
    "completed": "success",
    "failed": "error",
    "cancelled": "error",
    "included_in_payslip": "success",
}


# ============================================================================
# Settings
# ============================================================================

class CommissionsSettings(HubBaseModel):
    """Per-hub commissions settings (singleton per hub)."""

    __tablename__ = "commissions_settings"
    __table_args__ = (
        UniqueConstraint("hub_id", name="uq_commissions_settings_hub"),
    )

    # Commission defaults
    default_commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("10.00"), server_default="10.00",
    )
    calculation_basis: Mapped[str] = mapped_column(
        String(20), default="net", server_default="net",
    )

    # Payout settings
    payout_frequency: Mapped[str] = mapped_column(
        String(20), default="monthly", server_default="monthly",
    )
    payout_day: Mapped[int] = mapped_column(
        SmallInteger, default=1, server_default="1",
    )
    minimum_payout_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), server_default="0.00",
    )

    # Tax settings
    apply_tax_withholding: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
    )
    tax_withholding_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00"), server_default="0.00",
    )

    # Display
    show_commission_on_receipt: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
    )
    show_pending_commission: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
    )

    def __repr__(self) -> str:
        return f"<CommissionsSettings hub={self.hub_id}>"

    def calculate_tax(self, commission_amount: Decimal) -> tuple[Decimal, Decimal]:
        """Calculate tax withholding on a commission amount. Returns (net, tax)."""
        if not self.apply_tax_withholding or self.tax_withholding_rate <= 0:
            return commission_amount, Decimal("0")
        tax = (commission_amount * self.tax_withholding_rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )
        return commission_amount - tax, tax


# ============================================================================
# Commission Rule
# ============================================================================

class CommissionRule(HubBaseModel):
    """Commission rules for different scenarios."""

    __tablename__ = "commissions_rule"
    __table_args__ = (
        Index("ix_commissions_rule_hub_priority", "hub_id", "priority"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")

    # Type and value
    rule_type: Mapped[str] = mapped_column(
        String(20), default="percentage", server_default="percentage",
    )
    rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), server_default="0.00",
    )

    # Applicability — FK columns (all optional, null = global)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("staff_staffmember.id", ondelete="SET NULL"), nullable=True,
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("services_service.id", ondelete="SET NULL"), nullable=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("services_servicecategory.id", ondelete="SET NULL"), nullable=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("inventory_product.id", ondelete="SET NULL"), nullable=True,
    )

    # Tiered thresholds
    tier_thresholds: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]",
    )

    # Date range
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Priority and status
    priority: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
    )

    # Relationships
    transactions: Mapped[list[CommissionTransaction]] = relationship(
        "CommissionTransaction", back_populates="rule",
    )

    def __repr__(self) -> str:
        return f"<CommissionRule {self.name!r}>"

    @property
    def rule_type_display(self) -> str:
        return RULE_TYPE_CHOICES.get(self.rule_type, self.rule_type)

    def is_applicable_on(self, check_date: date) -> bool:
        if not self.is_active:
            return False
        if self.effective_from and check_date < self.effective_from:
            return False
        return not (self.effective_until and check_date > self.effective_until)

    def calculate_commission(self, amount: Decimal, sales_volume: Decimal | None = None) -> Decimal:
        """Calculate commission for given amount."""
        if self.rule_type == "flat":
            return self.rate
        elif self.rule_type == "percentage":
            return amount * (self.rate / Decimal("100"))
        elif self.rule_type == "tiered":
            if not self.tier_thresholds or sales_volume is None:
                return Decimal("0")
            for tier in sorted(self.tier_thresholds, key=lambda x: x.get("min_amount", 0)):
                min_amt = Decimal(str(tier.get("min_amount", 0)))
                max_amt = tier.get("max_amount")
                tier_rate = Decimal(str(tier.get("rate", 0)))
                if max_amt is None:
                    if sales_volume >= min_amt:
                        return amount * (tier_rate / Decimal("100"))
                else:
                    if min_amt <= sales_volume <= Decimal(str(max_amt)):
                        return amount * (tier_rate / Decimal("100"))
            return Decimal("0")
        return Decimal("0")


# ============================================================================
# Commission Transaction
# ============================================================================

class CommissionTransaction(HubBaseModel):
    """Individual commission transaction record."""

    __tablename__ = "commissions_transaction"
    __table_args__ = (
        Index("ix_commissions_trans_hub_staff_status", "hub_id", "staff_id", "status"),
        Index("ix_commissions_trans_hub_date", "hub_id", "transaction_date"),
    )

    # Staff — real FK + snapshot
    staff_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("staff_staffmember.id", ondelete="SET NULL"), nullable=True,
    )
    staff_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Source references — real FKs
    sale_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sales_sale.id", ondelete="SET NULL"), nullable=True,
    )
    sale_reference: Mapped[str] = mapped_column(String(100), default="", server_default="")
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("appointments_appointment.id", ondelete="SET NULL"), nullable=True,
    )

    # Amounts
    sale_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), server_default="0.00",
    )
    net_commission: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Rule
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("commissions_rule.id", ondelete="SET NULL"), nullable=True,
    )

    # Status and payout
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending",
    )
    payout_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("commissions_payout.id", ondelete="SET NULL"), nullable=True,
    )

    # Dates
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")

    # Relationships
    rule: Mapped[CommissionRule | None] = relationship(
        "CommissionRule", back_populates="transactions",
    )
    payout: Mapped[CommissionPayout | None] = relationship(
        "CommissionPayout", back_populates="transactions",
    )

    def __repr__(self) -> str:
        return f"<CommissionTransaction {self.staff_name}: {self.commission_amount} ({self.transaction_date})>"

    @property
    def status_display(self) -> str:
        return TRANSACTION_STATUS_CHOICES.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        return TRANSACTION_STATUS_COLORS.get(self.status, "medium")


# ============================================================================
# Commission Payout
# ============================================================================

class CommissionPayout(HubBaseModel):
    """Commission payout batch."""

    __tablename__ = "commissions_payout"

    reference: Mapped[str] = mapped_column(String(50), nullable=False)

    # Staff — real FK + snapshot
    staff_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("staff_staffmember.id", ondelete="SET NULL"), nullable=True,
    )
    staff_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Period
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Amounts
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), server_default="0.00",
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), server_default="0.00",
    )
    adjustments_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), server_default="0.00",
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), server_default="0.00",
    )
    transaction_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0",
    )

    # Status and payment
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft",
    )
    payment_method: Mapped[str] = mapped_column(String(20), default="", server_default="")
    payment_reference: Mapped[str] = mapped_column(String(100), default="", server_default="")

    # Workflow
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    paid_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")

    # Payroll integration — set when this payout is included in a Payslip
    payslip_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Relationships
    transactions: Mapped[list[CommissionTransaction]] = relationship(
        "CommissionTransaction", back_populates="payout",
    )
    adjustments_list: Mapped[list[CommissionAdjustment]] = relationship(
        "CommissionAdjustment", back_populates="payout",
    )

    def __repr__(self) -> str:
        return f"<CommissionPayout {self.reference} - {self.staff_name}>"

    @property
    def status_display(self) -> str:
        return PAYOUT_STATUS_CHOICES.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        return PAYOUT_STATUS_COLORS.get(self.status, "medium")

    @property
    def payment_method_display(self) -> str:
        return PAYMENT_METHOD_CHOICES.get(self.payment_method, self.payment_method)

    @property
    def can_be_modified(self) -> bool:
        return self.status in ("draft", "pending")

    def mark_included_in_payslip(self, payslip_id: uuid.UUID) -> None:
        """
        Mark this payout as included in a payslip.

        Sets status to 'included_in_payslip' and stores the payslip reference.
        This prevents double-counting across payroll runs.
        Called by PayrollCalculationService.confirm() — not by the collector.
        """
        self.status = "included_in_payslip"
        self.payslip_id = payslip_id


# ============================================================================
# Commission Adjustment
# ============================================================================

class CommissionAdjustment(HubBaseModel):
    """Manual commission adjustments."""

    __tablename__ = "commissions_adjustment"

    # Staff — real FK + snapshot
    staff_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("staff_staffmember.id", ondelete="SET NULL"), nullable=True,
    )
    staff_name: Mapped[str] = mapped_column(String(200), nullable=False)

    adjustment_type: Mapped[str] = mapped_column(
        String(20), default="correction", server_default="correction",
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    payout_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("commissions_payout.id", ondelete="SET NULL"), nullable=True,
    )

    adjustment_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Relationships
    payout: Mapped[CommissionPayout | None] = relationship(
        "CommissionPayout", back_populates="adjustments_list",
    )

    def __repr__(self) -> str:
        return f"<CommissionAdjustment {self.staff_name}: {self.amount} ({self.adjustment_type})>"

    @property
    def adjustment_type_display(self) -> str:
        return ADJUSTMENT_TYPE_CHOICES.get(self.adjustment_type, self.adjustment_type)
