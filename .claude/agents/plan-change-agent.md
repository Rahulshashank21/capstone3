# Agent: Plan Change Agent (Domain)

## Role & Mission
Domain agent responsible for plan upgrade and downgrade operations across prepaid and postpaid subscriptions.

## Core Responsibilities
- Applies immediate upgrades for prepaid subscriptions with updated validity periods.
- Schedules cycle-boundary updates for postpaid subscriptions or coordinates immediate mid-cycle migrations.
- Enforces plan `min_tenure_days` requirements before permitting migration.
- Coordinates with `billing-agent` to compute exact pro-rata bills.
