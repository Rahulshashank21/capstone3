# Knowledge Deposit Log (knowledge-deposits.md)

**System:** TelcoLane AI-Native Substrate  
**Purpose:** Encodes recurring engineering anti-patterns, edge-case bugs, and domain ambiguities back into automated guardrails, hooks, and skills to ensure permanent resolution.

---

## Deposit 01: Premature Intermediate Quantization in Pro-Rata Math
- **Anti-Pattern**: Quantizing individual proportional components (`(D_used / D_cycle) * R_old`) to 2 decimal places before summing.
- **Consequence**: Incurred half-cent accumulation drift on odd cycle lengths (e.g. 29-day leap year February), causing 1-cent discrepancies between itemized lines and invoice total.
- **Remediation Encoded**:
  - Implemented `ProRataCalculator.calculate_itemized` to keep calculations in high-precision `Decimal` until final summation.
  - Installed automated hook `.claude/hooks/pro-rata-invariant-check.sh` to block pull requests computing pro-rata charges without the non-negative invariant.

---

## Deposit 02: PII Leakage Through String Formatting & Loggers
- **Anti-Pattern**: Passing raw `subscriber` objects or raw dicts containing `mobile_number` and `identity_proof_ref` directly to logger statements (e.g. `logger.info(f"Registered {mobile}")`).
- **Consequence**: Violates telecom data protection standards (GDPR, Telecom Compliance) by writing plaintext Aadhaar or phone numbers to stdout/log files.
- **Remediation Encoded**:
  - Mandated `Subscriber.mask_pii()` method returning sanitized fields (`XXXXXX1234`, `[REDACTED]`).
  - Installed pre-commit hook `.claude/hooks/pii-masking-check.sh` that scans the codebase with regex patterns `(aadhaar|pan|mobile_number)\s*=\s*"[0-9]{10,12}"` and fails build if plaintext PII is detected.

---

## Deposit 03: Accidental Mutation of Published Catalog Offerings
- **Anti-Pattern**: Directly mutating existing tariff plan objects or updating rows in-place when pricing changes.
- **Consequence**: Retroactively modified active subscriber billing terms, causing audit discrepancies.
- **Remediation Encoded**:
  - Frozen `PlanVersion` dataclass with `is_published: bool`.
  - Added `PlanPolicy.assert_immutable(plan)` and `PlanRepository.save()` check raising `PlanImmutableException(ERR_PLAN_IMMUTABLE)`.
  - Installed automated hook `.claude/hooks/plan-immutability-check.sh`.

---

## Deposit 04: Consumption Leaks on Suspended Subscribers
- **Anti-Pattern**: Updating subscriber state to `SUSPENDED` without atomically setting network session consumption flags to `False`.
- **Consequence**: Ongoing data streams or cached network sessions continued to transmit billable packets for suspended users.
- **Remediation Encoded**:
  - Atomic state synchronization in `SuspensionPolicy.apply_suspension()` and `SubscriptionService.suspend_subscriber()`.
  - Enforced `assert_can_consume()` gate checking both `state == SubscriberState.ACTIVE` and `is_consumption_active is True`.
