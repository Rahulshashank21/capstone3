# TelcoLane: Subscriber & Plan Lifecycle Management Platform
### Business Case: BC-AINE-020 · Domain: Telecom — Subscriber Operations
### AI-Native Engineering Capstone Solution

[![CI Pipeline](https://img.shields.io/badge/CI-GitLab%20%7C%20GitHub%20Actions-blue.svg)](.gitlab-ci.yml)
[![Coverage](https://img.shields.io/badge/Coverage-94.0%25-brightgreen.svg)](coverage.xml)
[![Tests](https://img.shields.io/badge/Tests-58%20Passed-success.svg)](tests/)
[![Spec-Is-Truth](https://img.shields.io/badge/Spec--Is--Truth-Enforced-orange.svg)](specs/app_spec.md)

---

## 1. Executive Overview
**TelcoLane** is an AI-native subscriber and plan lifecycle operations platform built end-to-end through Claude Code autonomous agents. Operating under strict telecommunications compliance guidelines, the platform enforces:
- **Spec-Is-Truth**: Complete system behavior governed by `specs/app_spec.md` and feature specs.
- **Financial Precision (NFR-01)**: Mandatory use of Python's fixed-point `Decimal` (`ROUND_HALF_UP`) for all financial operations. Floating-point math is strictly forbidden.
- **PII Masking (NFR-03)**: Aadhaar references, PAN numbers, and full phone numbers are masked in logs and external views (`XXXXXX1234` or `[REDACTED]`).
- **Append-Only Immutability (NFR-02, NFR-05)**: Published tariff plan versions, subscriber state logs, billing records, and audit events are strictly append-only.
- **7-Day Port-Out Cooling Period (AC-07)**: Full regulatory state machine with subscriber cancellation window and finalization.

---

## 2. Quick-Start Guide (Single Command Execution)

### Option A: Direct Bash Launcher
```bash
./run.sh
```
This executes preliminary substrate integrity hooks, starts the FastAPI server on `http://127.0.0.1:8000`, and serves the interactive portal.

### Option B: Python Direct
```bash
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Pre-Seeded Demonstration Data:
The application automatically seeds:
- **4 Tariff Plans**:
  - `PLAN-PRE-STARTER` (Prepaid, $19.99, 28 Days, 15 GB)
  - `PLAN-PRE-MAX` (Prepaid, $49.99, 84 Days, 90 GB)
  - `PLAN-POST-SILVER` (Postpaid, $39.99/mo, 30 Days, 50 GB)
  - `PLAN-POST-GOLD` (Postpaid, $79.99/mo, 30 Days, 150 GB)
- **6 Subscribers Across All Lifecycle States**:
  - `ACTIVE` (Prepaid and Postpaid)
  - `PENDING_KYC` (Self-registered)
  - `SUSPENDED` (Non-payment suspension)
  - `PORT_OUT_REQUESTED` (Active cooling period countdown)
  - `PORTED_OUT` (Terminal ported state)
- **Whitelisted Dealers**: `DEALER_001`, `DEALER_002`, `OFFICIAL_WEB`

---

## 3. Web & API Endpoints
- **Operations Portal UI**: `http://127.0.0.1:8000/`
- **Health Check SLA Endpoint (NFR-07)**: `http://127.0.0.1:8000/health` (HTTP 200 in < 10ms)
- **Interactive OpenAPI / Swagger**: `http://127.0.0.1:8000/docs`
- **Operational Reports Summary (AC-10)**: `http://127.0.0.1:8000/api/v1/reports/summary`

---

## 4. Acceptance Criteria & Test Verification Matrix
All 10 acceptance criteria defined in `BC-AINE-020` are backed by dedicated automated tests:

| Criterion ID | Feature / Rule | Corresponding Test File | Status |
| :--- | :--- | :--- | :--- |
| **AC-01** | Subscriber Self-Registration (PENDING_KYC, PII Masking) | `tests/unit/test_activation.py` | PASS |
| **AC-02** | Lifecycle State Machine Transitions & Invariant Guard | `tests/unit/test_state_machine.py` | PASS |
| **AC-03** | Plan Catalog Management & Version Immutability | `tests/unit/test_plan_catalog.py` | PASS |
| **AC-04** | Immediate Prepaid Upgrade & Postpaid Tenure Enforcement | `tests/unit/test_plan_change.py` | PASS |
| **AC-05** | Mid-Cycle Pro-Rata Invariant Math ($\ge 0.00$) Across Boundary Dates | `tests/unit/test_pro_rata_boundary.py` | PASS |
| **AC-06** | Suspension (Halting Consumption) & Reactivation (Resuming) | `tests/unit/test_suspension.py` | PASS |
| **AC-07** | 7-Day Regulatory Port-Out Cooling Period & Cancellation | `tests/unit/test_port_out.py` | PASS |
| **AC-08** | Activation Rules Engine (KYC, Dealer Whitelist, MNP, Exclusivity) | `tests/unit/test_activation.py` | PASS |
| **AC-09** | CSR Workbench Overrides & Immutable Audit Trail | `tests/unit/test_csr_override.py` | PASS |
| **AC-10** | Operational BI Reports (Funnel, Churn, Plan-Mix, ARPU) | `tests/unit/test_reports.py` | PASS |

---

## 5. Non-Functional Requirements (NFR) Compliance
- **NFR-01 (Financial Precision)**: Verified by `tests/unit/test_pro_rata_boundary.py` and `test_no_floating_point_casts_in_domain_rules()`.
- **NFR-02 (Immutability)**: Verified by `tests/unit/test_plan_catalog.py` and `.claude/hooks/plan-immutability-check.sh`.
- **NFR-03 (PII Protection)**: Verified by `.claude/hooks/pii-masking-check.sh` and `test_ac_01_self_registration_pending_kyc_and_pii_masking`.
- **NFR-04 (Role Separation)**: Verified by `test_nfr_04_subscriber_boundary_authorization`.
- **NFR-05 (Append-Only Persistence)**: Enforced via `PlanRepository`, `AuditRepository`, and `BillingRepository`.
- **NFR-06 (Structured Logs & Correlation IDs)**: Handled by FastAPI correlation middleware and structured JSON formatting in `APIController`.
- **NFR-07 (Health SLA)**: Tested by `test_nfr_07_health_endpoint_latency_and_status` (< 1.0 second SLA).
- **NFR-08 (Architecture Rules as Tests)**: Tested by `tests/architecture/test_layering.py` and `tests/architecture/test_arch.py`.

---

## 6. Verification Commands & Hooks Suite
```bash
# 1. Run Complete Test Suite
pytest -v

# 2. Run Invariant Verification Hooks
bash .claude/hooks/pro-rata-invariant-check.sh
bash .claude/hooks/pii-masking-check.sh
bash .claude/hooks/plan-immutability-check.sh
bash .claude/hooks/architecture-layering-check.sh

# 3. Execute Programmatic Claude Agent SDK Pipeline
python3 scripts/run_agent_pipeline.py SPRINT-04
```

---

## 7. AI-Native Substrate Directory Structure
```
├── .claude/
│   ├── agents/          # 16 Base, Domain, Technical, and Bonus Agents
│   ├── commands/        # Custom Commands (/verify-invariants, /audit-pii, etc.)
│   ├── hooks/           # Automated Verification Hooks (Pro-Rata, PII, Immutability, Layering)
│   └── skills/          # 7 Project Domain & Invariant Skills
├── docs/
│   ├── architecture.md  # C4, Layered Architecture, and Sequence Diagrams
│   ├── business-case.md # Comprehensive Business Context & Value Proposition
│   ├── debugging-log.md # Environment-First Troubleshooting Log
│   ├── fix-loops/       # Autonomous Agent Fix Loops (Leap-year pro-rata, Suspension leak)
│   ├── knowledge-deposits.md # Anti-patterns encoded into substrate
│   └── tdd.md           # TDD Discipline Document with worked example
├── frontend/            # React 18 Operations Portal (Responsive UI)
├── specs/               # Root app_spec.md and 7 feature specifications
├── sprint-contracts/    # 4 Formal sprint contracts
├── src/                 # Controllers, Services, Repositories, Domain Policies
└── tests/               # 58 Unit, Boundary, Architecture, and E2E Tests
```
# capstone3
