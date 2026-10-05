# TelcoLane AI Substrate Rules

## Project Overview
TelcoLane is a Subscriber & Plan Lifecycle Management Platform operating under strict telecom compliance rules.

## Core Directives
1. Spec-Is-Truth: All code must conform strictly to specs/app_spec.md and feature specs.
2. Financial Precision: Use Decimal/BigDecimal for all charges, rents, and pro-rata math. Floating-point arithmetic is forbidden (NFR-01).
3. PII Masking: Never log or persist unmasked PII (Mobile Numbers, ID References). Mask format: `XXXXXX1234` or `[REDACTED]` (NFR-03).
4. Immutability: Published plans and audit logs are append-only.

## Test & Build Execution
- Run Unit Tests: `pytest tests/unit`
- Run Architecture Tests: `pytest tests/architecture`
- Run E2E Tests: `npx playwright test`
- Verification Hook Suite: `bash .claude/hooks/pro-rata-invariant-check.sh`
