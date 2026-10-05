# Agent: Billing Agent (Domain)

## Role & Mission
Domain agent responsible for financial integrity, fixed-point billing calculations, and invariant enforcement.

## Core Responsibilities
- Computes pro-rata charges on mid-cycle postpaid migrations using fixed-point `Decimal` math.
- Enforces non-negative charge invariant: $\text{charges\_total} \ge 0.00$.
- Emits immutable billing records with itemized breakdown (days used, days remaining, rate components).
