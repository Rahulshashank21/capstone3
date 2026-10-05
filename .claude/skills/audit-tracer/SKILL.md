---
name: audit-tracer
description: Ensures complete, append-only, tamper-evident audit trails for all sensitive subscriber state and override operations.
---

# Audit Tracer Skill

## Regulatory Audit Schema
Every mutation to subscriber state or financial attributes must record an immutable audit entry:
- `log_id`: Unique prefixed ID (`AUD-[a-f0-9]{8}`)
- `actor`: Caller username or ID (e.g., `CSR_AGENT_77`, `SUB-12345678`, `SYSTEM_JOB`)
- `role`: Role enum (`SUBSCRIBER`, `CSR`, `ADMIN`, `DEALER`)
- `action`: Canonical action name (e.g., `CSR_ACTIVATION_OVERRIDE`, `PLAN_CHANGE`, `PORT_OUT_INITIATED`)
- `reason_code`: Mandatory enumerated reason code for overrides or terminations
- `details`: Human-readable description with masked PII
- `timestamp`: UTC datetime stamp
