# TelcoLane AI Substrate Rules

## Project Overview
TelcoLane is a Subscriber & Plan Lifecycle Management Platform operating under strict telecom compliance and regulatory rules (Business Case: BC-AINE-020).

## Core Directives
1. **Spec-Is-Truth**: All code must conform strictly to `specs/app_spec.md` and feature specs (`specs/*_spec.md`). If code and specs conflict, the spec is authoritative.
2. **Financial Precision (NFR-01)**: Use `Decimal` (`ROUND_HALF_UP`) for all charges, rents, daily rates, and pro-rata math. Floating-point arithmetic (`float`) is forbidden.
3. **PII Masking (NFR-03)**: Never log or persist unmasked PII (Mobile Numbers, Identity References). Mask formats: `XXXXXX1234` or `[REDACTED]`.
4. **Append-Only Immutability (NFR-02, NFR-05)**: Published plans, subscriber state transition logs, billing records, and audit events are strictly append-only.
5. **Architectural Isolation (NFR-08)**: Clean layered architecture: Controller -> Service -> Repository -> Domain. Domain has zero external framework dependencies.

## Test & Build Execution
- Run Unit Tests: `pytest tests/unit`
- Run Architecture Tests: `pytest tests/architecture`
- Run All Tests with Coverage: `pytest --cov=src tests/`
- Run E2E Tests: `npx playwright test` (or `pytest tests/e2e`)
- Verification Hook Suite:
  - `bash .claude/hooks/pro-rata-invariant-check.sh`
  - `bash .claude/hooks/pii-masking-check.sh`
  - `bash .claude/hooks/plan-immutability-check.sh`
  - `bash .claude/hooks/architecture-layering-check.sh`
- Start Application: `python -m src.main` or `./run.sh`
