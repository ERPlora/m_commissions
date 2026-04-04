"""
Test fixtures for the commissions module.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from commissions.models import (
    CommissionAdjustment,
    CommissionPayout,
    CommissionRule,
    CommissionTransaction,
    CommissionsSettings,
)


@pytest.fixture
def hub_id():
    """Test hub UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_settings(hub_id):
    """Create sample commissions settings (not persisted)."""
    return CommissionsSettings(
        hub_id=hub_id,
        default_commission_rate=Decimal("10.00"),
        calculation_basis="net",
        payout_frequency="monthly",
        payout_day=1,
    )


@pytest.fixture
def sample_rule(hub_id):
    """Create a sample commission rule (not persisted)."""
    return CommissionRule(
        hub_id=hub_id,
        name="Standard 10%",
        rule_type="percentage",
        rate=Decimal("10.00"),
        priority=10,
        is_active=True,
    )


@pytest.fixture
def sample_flat_rule(hub_id):
    """Create a sample flat commission rule (not persisted)."""
    return CommissionRule(
        hub_id=hub_id,
        name="Flat $5",
        rule_type="flat",
        rate=Decimal("5.00"),
        priority=5,
        is_active=True,
    )


@pytest.fixture
def sample_transaction(hub_id):
    """Create a sample transaction (not persisted)."""
    return CommissionTransaction(
        hub_id=hub_id,
        staff_name="Juan Lopez",
        sale_amount=Decimal("100.00"),
        commission_rate=Decimal("10.00"),
        commission_amount=Decimal("10.00"),
        tax_amount=Decimal("0.00"),
        net_commission=Decimal("10.00"),
        status="pending",
        transaction_date=date.today(),
    )


@pytest.fixture
def sample_payout(hub_id):
    """Create a sample payout (not persisted)."""
    return CommissionPayout(
        hub_id=hub_id,
        reference="PAY-202604-0001",
        staff_name="Juan Lopez",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        gross_amount=Decimal("100.00"),
        tax_amount=Decimal("0.00"),
        net_amount=Decimal("100.00"),
        transaction_count=5,
        status="pending",
    )


@pytest.fixture
def sample_adjustment(hub_id):
    """Create a sample adjustment (not persisted)."""
    return CommissionAdjustment(
        hub_id=hub_id,
        staff_name="Juan Lopez",
        adjustment_type="bonus",
        amount=Decimal("25.00"),
        reason="Monthly performance bonus",
        adjustment_date=date.today(),
    )
