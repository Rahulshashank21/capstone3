# TelcoLane Core Application Specification (app_spec.md)

**Document Version:** 1.0.0  
**Business Case ID:** BC-AINE-020  
**Domain:** Telecom — Subscriber & Plan Lifecycle Management  
**Status:** Approved / Spec-Is-Truth  

---

## 1. Executive Summary & Problem Context
TelcoLane is a unified subscriber and plan lifecycle operations platform for next-generation telecommunication operators. The platform handles subscriber self-registration, KYC verification, dealer-driven activations, MNP port-in validations, catalog lifecycle management (prepaid validity & postpaid cycle plans), pro-rata mid-cycle billing, service suspensions/resumptions, and a compliant 7-day port-out cooling-period state machine with CSR override workflows.

Operating under strict telecom compliance regulations, TelcoLane enforces:
1. **Spec-Is-Truth Principle**: The specifications define exact system behavior. Code must strictly reflect the acceptance criteria.
2. **Financial Precision (NFR-01)**: Mandatory use of fixed-point `Decimal` arithmetic (`ROUND_HALF_UP`) for all financial math, monthly rents, daily rates, and pro-rata billing. Floating-point arithmetic is strictly forbidden.
3. **Data Privacy & PII Masking (NFR-03)**: Aadhaar references, PAN numbers, and full mobile numbers are masked in logs and external views (`XXXXXX1234` or `[REDACTED]`).
4. **Append-Only Immutability (NFR-02, NFR-05)**: Published plan versions, audit logs, billing records, state transitions, and CSR overrides cannot be updated or deleted in place.

---

## 2. Actors & Role-Based Access Control (NFR-04)
| Role | Identity & Permissions |
| :--- | :--- |
| `SUBSCRIBER` | End-user. Can self-register, view own plan/usage, request upgrades/downgrades, request suspension/resumption, initiate port-out or cancel within cooling period. Cannot view other subscribers. |
| `DEALER` | Certified point-of-sale agent. Validated by dealer code whitelist (`DEALER_001`, `DEALER_002`, `OFFICIAL_WEB`). Initiates customer on-boarding and SIM activations. |
| `CSR` (Customer Service Rep) | Operational support. Reviews exception queues, executes overrides with mandatory reason codes, inspects audit trails. |
| `ADMIN` | Operational executive. Publishes catalog versions, configures business rules, views activation funnel, churn analytics, plan-mix distribution, and ARPU reports. |

---

## 3. High-Level Architectural Structure
The system enforces a clean, layered architectural boundary:
```
+-------------------------------------------------------+
|                API / Controller Layer                 |
|  - Role-based authorization & authentication context  |
|  - Request correlation IDs & structured JSON logging  |
|  - Input validation and exception serialization       |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|                    Service Layer                      |
|  - SubscriptionService, PlanService, BillingService   |
|  - ReportingService, CSROverrideService               |
|  - Orchestrates domain policies and repositories      |
|  - Emits immutable audit logs                         |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|                  Repositories Layer                   |
|  - SubscriberRepository, PlanRepository               |
|  - AuditLogRepository, BillingRecordRepository        |
|  - Append-only records and thread-safe persistence    |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|                     Domain Layer                      |
|  - Domain Models (Subscriber, PlanVersion, AuditLog)  |
|  - State Machine Validator (Lifecycle transitions)    |
|  - ProRataCalculator (Fixed-point mathematical engine)|
|  - Policies: Activation, PlanChange, PortOut, CSR     |
|  - PII Masking utilities and Custom Domain Exceptions  |
+-------------------------------------------------------+
```

---

## 4. Subscriber Lifecycle State Machine
```
   [Self-Registration]
           |
           v
   +---------------+
   |  PENDING_KYC  |
   +---------------+
      |         |
      | (Pass)  | (Fail / Reject)
      v         v
  +--------+  +------------+
  | ACTIVE |  | TERMINATED |
  +--------+  +------------+
    |    ^          ^
    |    | (Resume) |
    |    +-------+  |
    v            |  |
+-----------+    |  |
| SUSPENDED |----+  |
+-----------+       |
    |               |
    v (Port Request)|
+--------------------+
| PORT_OUT_REQUESTED |
+--------------------+
    |           |
    | (7-day    | (Cancel within
    |  expire)  |  7 days)
    v           v
+------------+ +--------+
| PORTED_OUT | | ACTIVE |
+------------+ +--------+
```

### Valid Lifecycle State Transitions:
1. `PENDING_KYC` -> `ACTIVE`, `TERMINATED`
2. `ACTIVE` -> `SUSPENDED`, `PORT_OUT_REQUESTED`, `TERMINATED`
3. `SUSPENDED` -> `ACTIVE`, `TERMINATED`
4. `PORT_OUT_REQUESTED` -> `ACTIVE` (cancellation during 7-day cooling period), `PORTED_OUT` (finalization), `TERMINATED`
5. `PORTED_OUT` -> None (terminal)
6. `TERMINATED` -> None (terminal)

Any transition outside this matrix raises `InvalidSubscriberStateException` with reason code `ERR_INVALID_STATE_TRANSITION`.

---

## 5. Non-Functional Requirements (NFR)
- **NFR-01: Financial Precision**  
  All financial computations (monthly rents, pro-rata charges, daily rates) use `Decimal` with `ROUND_HALF_UP` precision to 2 decimal places. Floating-point arithmetic (`float`) is forbidden.
- **NFR-02: Immutability**  
  Published plan versions, subscriber state transition logs, billing records, port-out events, and CSR overrides are strictly append-only. Modifying a published plan raises `PlanImmutableException`.
- **NFR-03: PII Masking**  
  Full mobile numbers are masked as `XXXXXX1234`. National identity proofs (Aadhaar, PAN) are replaced by `[REDACTED]` in logs, audit records, and consumer responses.
- **NFR-04: Role Separation**  
  Controller layer verifies role context (`SUBSCRIBER`, `CSR`, `ADMIN`, `DEALER`). A subscriber cannot access data of another subscriber. CSR actions require reason codes.
- **NFR-05: Append-Only Storage & Catalog Migrations**  
  In-memory / persistence structures append new versions (`version = version + 1`) rather than overwriting existing records.
- **NFR-06: Structured JSON Logs**  
  System outputs structured JSON log entries containing `timestamp`, `level`, `correlation_id`, `actor`, `action`, and masked `subscriber_id`.
- **NFR-07: Health Endpoint Responsiveness**  
  A dedicated `/health` endpoint responds with HTTP 200 and `{"status": "UP", "timestamp": ...}` within 1 second of startup.
- **NFR-08: Architectural Guardrails as Tests**  
  Automated tests enforce domain layer isolation (no framework imports), single ACTIVE subscription per mobile number, plan immutability, and pro-rata mathematical invariants.

---

## 6. Functional Acceptance Criteria Index (AC-01 through AC-10)

### AC-01: Subscriber Self-Registration
- **Given** an unregistered mobile number, identity proof reference (Aadhaar/Passport/PAN stub), and preferred plan type (`PREPAID` or `POSTPAID`),
- **When** the registration endpoint is called,
- **Then** a subscriber entity is created in `PENDING_KYC` state with a unique `SUB-` identifier, and returned data contains masked PII.

### AC-02: Subscriber Lifecycle State Transitions
- **Given** a subscriber in any lifecycle state,
- **When** an invalid state transition is attempted (e.g., `PENDING_KYC` -> `PORT_OUT_REQUESTED` or `PORTED_OUT` -> `ACTIVE`),
- **Then** the transition is blocked and `InvalidSubscriberStateException` is raised with reason code `ERR_INVALID_STATE_TRANSITION`.

### AC-03: Plan Catalog Management & Immutability
- **Given** the telecom plan catalog supporting `PREPAID` (validity in days, quota in GB) and `POSTPAID` (monthly billing cycle, quota in GB),
- **When** a plan version is marked `is_published=True`,
- **Then** any attempt to alter rent, quota, or validity raises `PlanImmutableException` (`ERR_PLAN_IMMUTABLE`). New revisions must be saved as new versions.

### AC-04: Plan Upgrade / Downgrade Execution
- **Given** an ACTIVE subscriber,
- **When** requesting a plan change:
  - For `PREPAID`, the change is effective immediately upon recharge/activation.
  - For `POSTPAID`, the change is scheduled from the next billing cycle unless mid-cycle pro-rata is confirmed.
- **Then** plan eligibility rules (e.g., minimum tenure days) are strictly enforced; failing tenure raises `PlanChangeTenureException`.

### AC-05: Pro-Rata Billing Mathematical Invariant
- **Given** a mid-cycle postpaid plan change with old monthly rent $R_{old}$, new monthly rent $R_{new}$, days elapsed $D_{used}$, and cycle duration $D_{cycle}$,
- **When** computing the pro-rata invoice:
  $$\text{charges\_total} = \left(\frac{D_{used}}{D_{cycle}} \times R_{old}\right) + \left(\frac{D_{cycle} - D_{used}}{D_{cycle}} \times R_{new}\right)$$
- **Then** the charge is computed using `Decimal` rounded to 2 decimal places, and the invariant $\text{charges\_total} \ge 0.00$ must strictly hold.

### AC-06: Suspension & Consumption Halting
- **Given** an ACTIVE subscriber,
- **When** a suspension is requested by the subscriber or triggered by non-payment,
- **Then** the subscriber moves to `SUSPENDED` state and network consumption (data/voice/SMS counters) is halted.
- **When** reactivation is invoked,
- **Then** the subscriber returns to `ACTIVE` and consumption capability is restored.

### AC-07: Port-Out Cooling-Period State Machine
- **Given** an ACTIVE subscriber requesting port-out,
- **When** port-out is initiated,
- **Then** subscriber transitions to `PORT_OUT_REQUESTED` with a 7-day cooling-period timestamp.
- **When** the subscriber cancels within 7 days (168 hours),
- **Then** state transitions back to `ACTIVE` and port-out timestamp is cleared.
- **When** cooling period expires (>= 7 days),
- **Then** state transitions to `PORTED_OUT`.

### AC-08: Activation Rule Engine (KYC, Dealer, MNP)
- **Given** a subscriber in `PENDING_KYC` state,
- **When** activation is submitted:
  - If `kyc_status != "VERIFIED"`, raise `ActivationFailedException` with code `ERR_KYC_FAILED`.
  - If `dealer_code` is not in approved registry (`DEALER_001`, `DEALER_002`, `OFFICIAL_WEB`), raise `ActivationFailedException` with code `ERR_INVALID_DEALER`.
  - If `mnp_status == "REJECTED"`, raise `ActivationFailedException` with code `ERR_MNP_REJECTED`.
  - If mobile number already has an `ACTIVE` subscription, raise `ActivationFailedException` with code `ERR_DUPLICATE_ACTIVE_NUMBER`.
- **Then** only when all checks pass, subscriber transitions to `ACTIVE`.

### AC-09: CSR Exception Overrides & Audit Trail
- **Given** a subscriber rejected during activation or plan-change due to rule failure,
- **When** an authorized CSR or Admin executes an override with a valid reason code (e.g. `OVERRIDE_KYC_MANUAL`),
- **Then** the action succeeds, transitions the subscriber to `ACTIVE`, and generates an append-only `AuditLog` entry containing `actor`, `role`, `timestamp`, `reason_code`, and `details`.

### AC-10: Admin Operational Reports & Analytics
- **Given** existing subscriber records, state transitions, and billing events,
- **When** an Admin queries operational dashboards,
- **Then** the system returns:
  1. **Activation Funnel**: Total registered vs active conversion rate.
  2. **Monthly Churn Rate**: Count and percentage of terminated and ported-out subscribers grouped by reason.
  3. **Plan-Mix Distribution**: Proportions of PREPAID vs POSTPAID active plans.
  4. **Average Revenue Per User (ARPU)**: Calculated based on active monthly plan rents.

---

## 7. Verification & Quality Gates
- **Pytest Unit Suite**: 100% of acceptance criteria covered by tagged test methods (`test_ac_01_...` to `test_ac_10_...`).
- **Layering Architecture Tests**: Enforced through import assertions and `import-linter`.
- **Invariant Hooks**: Execution of `.claude/hooks/pro-rata-invariant-check.sh`, `pii-masking-check.sh`, and `plan-immutability-check.sh`.
- **Playwright E2E Suite**: Full browser validation for registration, plan change, port-out, and CSR workflows.
