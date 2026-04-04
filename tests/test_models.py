"""
Tests for commissions module models.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from commissions.models import (
    ADJUSTMENT_TYPE_CHOICES,
    PAYOUT_STATUS_CHOICES,
    PAYMENT_METHOD_CHOICES,
    RULE_TYPE_CHOICES,
    TRANSACTION_STATUS_CHOICES,
    CommissionRule,
)


class TestCommissionsSettings:
    def test_calculate_tax_no_withholding(self, sample_settings):
        sample_settings.apply_tax_withholding = False
        net, tax = sample_settings.calculate_tax(Decimal("100.00"))
        assert net == Decimal("100.00")
        assert tax == Decimal("0")

    def test_calculate_tax_with_withholding(self, sample_settings):
        sample_settings.apply_tax_withholding = True
        sample_settings.tax_withholding_rate = Decimal("15.00")
        net, tax = sample_settings.calculate_tax(Decimal("100.00"))
        assert tax == Decimal("15.00")
        assert net == Decimal("85.00")

    def test_calculate_tax_zero_rate(self, sample_settings):
        sample_settings.apply_tax_withholding = True
        sample_settings.tax_withholding_rate = Decimal("0.00")
        net, tax = sample_settings.calculate_tax(Decimal("50.00"))
        assert net == Decimal("50.00")
        assert tax == Decimal("0")


class TestCommissionRule:
    def test_percentage_calculation(self, sample_rule):
        result = sample_rule.calculate_commission(Decimal("200.00"))
        assert result == Decimal("20.00")

    def test_flat_calculation(self, sample_flat_rule):
        result = sample_flat_rule.calculate_commission(Decimal("200.00"))
        assert result == Decimal("5.00")

    def test_tiered_calculation(self, hub_id):
        rule = CommissionRule(
            hub_id=hub_id,
            name="Tiered",
            rule_type="tiered",
            tier_thresholds=[
                {"min_amount": 0, "max_amount": 1000, "rate": 5},
                {"min_amount": 1000, "max_amount": None, "rate": 10},
            ],
        )
        # Low volume tier
        result = rule.calculate_commission(Decimal("100.00"), sales_volume=Decimal("500"))
        assert result == Decimal("5.00")

        # High volume tier
        result = rule.calculate_commission(Decimal("100.00"), sales_volume=Decimal("1500"))
        assert result == Decimal("10.00")

    def test_tiered_no_volume(self, hub_id):
        rule = CommissionRule(hub_id=hub_id, name="T", rule_type="tiered", tier_thresholds=[])
        assert rule.calculate_commission(Decimal("100.00")) == Decimal("0")

    def test_is_applicable_on_active(self, sample_rule):
        assert sample_rule.is_applicable_on(date.today()) is True

    def test_is_applicable_on_inactive(self, sample_rule):
        sample_rule.is_active = False
        assert sample_rule.is_applicable_on(date.today()) is False

    def test_is_applicable_on_date_range(self, hub_id):
        rule = CommissionRule(
            hub_id=hub_id, name="Date Range", rule_type="percentage",
            effective_from=date(2026, 1, 1), effective_until=date(2026, 12, 31),
            is_active=True,
        )
        assert rule.is_applicable_on(date(2026, 6, 15)) is True
        assert rule.is_applicable_on(date(2025, 6, 15)) is False
        assert rule.is_applicable_on(date(2027, 1, 1)) is False

    def test_rule_type_display(self, sample_rule):
        assert sample_rule.rule_type_display == "Percentage"

    def test_repr(self, sample_rule):
        assert "Standard 10%" in repr(sample_rule)


class TestCommissionTransaction:
    def test_status_display(self, sample_transaction):
        assert sample_transaction.status_display == "Pending"

    def test_status_color(self, sample_transaction):
        assert sample_transaction.status_color == "warning"
        sample_transaction.status = "approved"
        assert sample_transaction.status_color == "success"

    def test_repr(self, sample_transaction):
        assert "Juan Lopez" in repr(sample_transaction)


class TestCommissionPayout:
    def test_status_display(self, sample_payout):
        assert sample_payout.status_display == "Pending Approval"

    def test_status_color(self, sample_payout):
        assert sample_payout.status_color == "warning"

    def test_can_be_modified(self, sample_payout):
        sample_payout.status = "draft"
        assert sample_payout.can_be_modified is True
        sample_payout.status = "completed"
        assert sample_payout.can_be_modified is False

    def test_payment_method_display(self, sample_payout):
        sample_payout.payment_method = "bank_transfer"
        assert sample_payout.payment_method_display == "Bank Transfer"


class TestCommissionAdjustment:
    def test_adjustment_type_display(self, sample_adjustment):
        assert sample_adjustment.adjustment_type_display == "Bonus"

    def test_repr(self, sample_adjustment):
        assert "Juan Lopez" in repr(sample_adjustment)


class TestChoiceDicts:
    def test_all_choices_have_values(self):
        for choices in (
            RULE_TYPE_CHOICES, TRANSACTION_STATUS_CHOICES,
            PAYOUT_STATUS_CHOICES, PAYMENT_METHOD_CHOICES,
            ADJUSTMENT_TYPE_CHOICES,
        ):
            assert len(choices) > 0
            for key, value in choices.items():
                assert isinstance(key, str)
                assert isinstance(value, str)
