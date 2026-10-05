---
name: plan-rule-evaluator
description: Validates telecom plan configuration, tenure requirements, immutability, and migration rules.
---

# Plan Rule Evaluator Skill

## Overview
This skill provides deterministic evaluation of plan definitions, versioning rules, and subscriber eligibility for plan upgrades and downgrades.

## Responsibilities
- **Immutability Check**: Verify that any plan with `is_published=True` cannot be mutated.
- **Plan Family Rules**: Validate that prepaid plans specify validity days (> 0) and that postpaid plans specify positive monthly rental fees.
- **Tenure Check**: Evaluate whether a subscriber's tenure on their current plan satisfies `min_tenure_days` before approving migration.

## Usage Guide
When evaluating a plan change request:
1. Retrieve the subscriber's current plan and activation timestamp.
2. Calculate days elapsed: `days_elapsed = (current_time - plan_activated_at).days`.
3. Check `days_elapsed >= current_plan.min_tenure_days`.
4. If not satisfied, reject with `ERR_MINIMUM_TENURE_NOT_MET` unless CSR override with `OVERRIDE_TENURE_WAIVER` is attached.
