"""Initial commissions module tables.

Revision ID: 001
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CommissionsSettings
    op.create_table(
        "commissions_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hub_id", sa.Uuid(), nullable=False),
        sa.Column("default_commission_rate", sa.Numeric(precision=5, scale=2), server_default="10.00", nullable=False),
        sa.Column("calculation_basis", sa.String(length=20), server_default="net", nullable=False),
        sa.Column("payout_frequency", sa.String(length=20), server_default="monthly", nullable=False),
        sa.Column("payout_day", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("minimum_payout_amount", sa.Numeric(precision=10, scale=2), server_default="0.00", nullable=False),
        sa.Column("apply_tax_withholding", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("tax_withholding_rate", sa.Numeric(precision=5, scale=2), server_default="0.00", nullable=False),
        sa.Column("show_commission_on_receipt", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("show_pending_commission", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hub_id", name="uq_commissions_settings_hub"),
    )

    # CommissionRule
    op.create_table(
        "commissions_rule",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hub_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("rule_type", sa.String(length=20), server_default="percentage", nullable=False),
        sa.Column("rate", sa.Numeric(precision=10, scale=2), server_default="0.00", nullable=False),
        sa.Column("staff_id", sa.Uuid(), nullable=True),
        sa.Column("service_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("tier_thresholds", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_until", sa.Date(), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_staffmember.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["service_id"], ["services_service.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["category_id"], ["services_servicecategory.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["inventory_product.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commissions_rule_hub_priority", "commissions_rule", ["hub_id", "priority"])

    # CommissionPayout (must be created before CommissionTransaction due to FK)
    op.create_table(
        "commissions_payout",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hub_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=50), nullable=False),
        sa.Column("staff_id", sa.Uuid(), nullable=True),
        sa.Column("staff_name", sa.String(length=200), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(precision=10, scale=2), server_default="0.00", nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=10, scale=2), server_default="0.00", nullable=False),
        sa.Column("adjustments_amount", sa.Numeric(precision=10, scale=2), server_default="0.00", nullable=False),
        sa.Column("net_amount", sa.Numeric(precision=10, scale=2), server_default="0.00", nullable=False),
        sa.Column("transaction_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("payment_method", sa.String(length=20), server_default="", nullable=False),
        sa.Column("payment_reference", sa.String(length=100), server_default="", nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.Uuid(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_staffmember.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # CommissionTransaction
    op.create_table(
        "commissions_transaction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hub_id", sa.Uuid(), nullable=False),
        sa.Column("staff_id", sa.Uuid(), nullable=True),
        sa.Column("staff_name", sa.String(length=200), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=True),
        sa.Column("sale_reference", sa.String(length=100), server_default="", nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=True),
        sa.Column("sale_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("commission_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=10, scale=2), server_default="0.00", nullable=False),
        sa.Column("net_commission", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("payout_id", sa.Uuid(), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_staffmember.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales_sale.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments_appointment.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rule_id"], ["commissions_rule.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payout_id"], ["commissions_payout.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commissions_trans_hub_staff_status", "commissions_transaction", ["hub_id", "staff_id", "status"])
    op.create_index("ix_commissions_trans_hub_date", "commissions_transaction", ["hub_id", "transaction_date"])

    # CommissionAdjustment
    op.create_table(
        "commissions_adjustment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hub_id", sa.Uuid(), nullable=False),
        sa.Column("staff_id", sa.Uuid(), nullable=True),
        sa.Column("staff_name", sa.String(length=200), nullable=False),
        sa.Column("adjustment_type", sa.String(length=20), server_default="correction", nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payout_id", sa.Uuid(), nullable=True),
        sa.Column("adjustment_date", sa.Date(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_staffmember.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payout_id"], ["commissions_payout.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("commissions_adjustment")
    op.drop_index("ix_commissions_trans_hub_date", table_name="commissions_transaction")
    op.drop_index("ix_commissions_trans_hub_staff_status", table_name="commissions_transaction")
    op.drop_table("commissions_transaction")
    op.drop_table("commissions_payout")
    op.drop_index("ix_commissions_rule_hub_priority", table_name="commissions_rule")
    op.drop_table("commissions_rule")
    op.drop_table("commissions_settings")
