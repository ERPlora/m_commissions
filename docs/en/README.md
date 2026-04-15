# Commissions (module: `commissions`)

Sales commission rules, tracking, and payouts for staff members.

## Purpose

The Commissions module automates the calculation and payout of sales commissions. When a sale completes, the module evaluates matching commission rules (by employee, service, product, or global) and auto-generates commission transactions. Managers can review, approve, and process payouts on a configurable frequency (weekly, bi-weekly, monthly, or custom).

Commission rules support three calculation types: flat amount, percentage of sale, and tiered (based on cumulative sales volume). The calculation basis can be gross sales, net sales (after discounts), or profit margin.

Payouts can be paid via cash, bank transfer, check, or folded into payroll.

## Models

- `CommissionsSettings` — Singleton per hub. Controls default payout frequency, calculation basis, and auto-approval thresholds.
- `CommissionRule` — Rule definition: name, type (flat/percentage/tiered), rate, priority, effective date range, employee/service/product scoping.
- `CommissionTransaction` — Generated commission entry per sale per employee. Status: pending / approved / paid / cancelled / adjusted.
- `CommissionPayout` — Aggregated payout batch for a staff member over a period. Status: draft / pending / approved / processing / completed / failed / cancelled / included_in_payslip.
- `CommissionAdjustment` — Manual bonus, correction, deduction, or refund adjustment on top of calculated commissions.

## Routes

`GET /m/commissions/` — Overview dashboard with stats
`GET /m/commissions/transactions` — Transaction list with filters
`GET /m/commissions/payouts` — Payout list
`GET /m/commissions/rules` — Rule management
`GET /m/commissions/adjustments` — Manual adjustment management
`GET /m/commissions/settings` — Module settings

## API

`GET /api/v1/m/commissions/rules` — List active commission rules
`GET /api/v1/m/commissions/transactions` — List commission transactions
`GET /api/v1/m/commissions/payouts` — List payouts

## Events

### Consumed

`sales.completed` — Auto-generates `CommissionTransaction` entries for matching rules when a sale is completed.

## Hooks

### Emitted (actions other modules can subscribe to)

`commissions.payout_completed` — Fired when a payout is marked completed. Payload: `payout`.

## Dependencies

- `staff`
- `services`
- `inventory`
- `sales`
- `appointments`

## Pricing

Free.
