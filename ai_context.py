"""
Commissions module AI context — injected into the LLM system prompt.

Provides the LLM with knowledge about the module's models, relationships,
and standard operating procedures.
"""

CONTEXT = """
## Commissions Module

Models: CommissionsSettings, CommissionRule, CommissionTransaction, CommissionPayout, CommissionAdjustment.

### CommissionsSettings (singleton per hub)
- `default_commission_rate` (%, default 10.00)
- `calculation_basis`: 'gross' | 'net' | 'profit' — what percentage is applied to
- `payout_frequency`: 'weekly' | 'biweekly' | 'monthly' | 'custom'
- `payout_day`: Day of month/week for payouts (1-31)
- `minimum_payout_amount`
- `apply_tax_withholding`, `tax_withholding_rate` (%)
- `show_commission_on_receipt`, `show_pending_commission`

### CommissionRule
- `name`, `description`, `rule_type` ('flat' | 'percentage' | 'tiered'), `rate`
- `staff_id` FK (null = all staff), `service_id`, `category_id`, `product_id`
- `tier_thresholds` (JSON): [{min_amount, max_amount, rate}]
- `effective_from`, `effective_until`, `priority` (higher = first), `is_active`

### CommissionTransaction
- `staff_id` FK + `staff_name` snapshot
- `sale_id` FK + `sale_reference`, `appointment_id` FK
- `sale_amount`, `commission_rate`, `commission_amount`, `tax_amount`, `net_commission`
- `rule_id` FK, `status` ('pending' | 'approved' | 'paid' | 'cancelled' | 'adjusted')
- `payout_id` FK, `transaction_date`, `approved_at`, `approved_by_id`

### CommissionPayout
- `reference` (auto: PAY-{YYYYMM}-{seq}), `staff_id` FK + `staff_name`
- `period_start`, `period_end`, `gross_amount`, `tax_amount`, `adjustments_amount`, `net_amount`
- `status` ('draft' | 'pending' | 'approved' | 'processing' | 'completed' | 'failed' | 'cancelled')
- `payment_method`, `payment_reference`, `approved_at/by`, `paid_at/by`

### CommissionAdjustment
- `staff_id` FK + `staff_name`, `adjustment_type` ('bonus' | 'correction' | 'deduction' | 'refund_adjustment' | 'other')
- `amount`, `reason`, `payout_id` FK, `adjustment_date`, `created_by_id`

### Restrictions
- Commission rate must be > 0.
- If both effective_from and effective_until are set, effective_from must be before effective_until.
- Cannot delete a commission rule that has pending or approved transactions — resolve or reassign first.

### Key Flows
1. Sale completes → auto-create CommissionTransaction (status='pending')
2. Manager approves → status='approved'
3. Create payout for staff+period → link approved transactions
4. Process payout → status='completed', transactions → 'paid'
5. Adjustments: manual bonus/correction linked to payout

### Relationships
- CommissionRule.staff → staff.StaffMember
- CommissionTransaction.sale → sales.Sale
- CommissionTransaction.appointment → appointments.Appointment
- CommissionPayout.transactions → CommissionTransaction set
"""

SOPS = [
    {
        "id": "commission_summary",
        "triggers_es": ["resumen comisiones", "comisiones del mes", "cuanto han ganado"],
        "triggers_en": ["commission summary", "commissions this month", "how much earned"],
        "steps": ["get_commission_summary"],
        "modules_required": ["commissions"],
    },
    {
        "id": "create_commission_rule",
        "triggers_es": ["crear regla comision", "nueva comision", "configurar comisiones"],
        "triggers_en": ["create commission rule", "new commission", "setup commissions"],
        "steps": ["create_commission_rule"],
        "modules_required": ["commissions"],
    },
    {
        "id": "list_commission_rules",
        "triggers_es": ["ver reglas comision", "reglas de comisiones"],
        "triggers_en": ["list commission rules", "show commission rules"],
        "steps": ["list_commission_rules"],
        "modules_required": ["commissions"],
    },
]
