# Agent Registry & Capabilities Index

| Agent Name | Scope | Key Responsibility |
| :--- | :--- | :--- |
| `activation-agent` | Domain | Validates dealer code, KYC stub, MNP status, and transitions subscriber to ACTIVE state |
| `plan-change-agent` | Domain | Computes pro-rata postpaid bills and immediate prepaid upgrades |
| `port-out-agent` | Domain | Controls the 7-day cooling-period state machine and cancellation flows |
| `state-machine-validator` | Technical | Verifies legal state transitions and prevents illegal multi-active subscriptions |
| `billing-agent` | Domain | Computes cycle billing, pro-rata adjustments, and enforces non-negative invariants |
| `csr-override-agent` | Domain | Manages operational exception overrides and ensures immutable audit logs |
| `planner` | Harness Foundation | Decomposes business requirements into actionable sprint backlog tickets |
| `generator` | Harness Foundation | Generates production code complying strictly with specifications |
| `evaluator` | Harness Foundation | Audits code against rubrics, acceptance criteria, and invariant hooks |
| `security-reviewer` | Harness Foundation | Enforces PII masking, authentication boundaries, and audit logging |
| `test-engineer` | Harness Foundation | Implements comprehensive unit, boundary, and architectural tests |
| `design-critic` | Harness Foundation | Evaluates UI usability, accessibility, and responsive viewport behavior |
| `ui-designer` | Harness Foundation | Creates interactive web components matching telecom user journeys |
| `janitor` | Bonus Substrate | Cleans temporary build artifacts, enforces code styling, and removes stale files |
| `performance-auditor` | Bonus Substrate | Benchmarks pro-rata calculation latency and state transition throughput |
| `doc-writer` | Bonus Substrate | Keeps specs, architecture docs, and sprint contracts synchronized with code |
