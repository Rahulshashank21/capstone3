# Feature Specification: CSR Exception Overrides & Audit Trail (AC-09)

**Specification ID:** SPEC-CSR-OVERRIDE-01  
**Target Criteria:** AC-09, NFR-02, NFR-04  
**Domain Area:** Customer Service Workbench & Compliance Auditing  

---

## 1. Overview
Automated business rules (such as OCR KYC document validation, dealer status, or minimum plan tenure) may reject valid customers due to false positives, edge-case credentials, or special executive dispensations.

The CSR Workbench allows authorized Customer Service Representatives (`CSR`) and System Administrators (`ADMIN`):
1. To inspect queued rule exceptions.
2. To explicitly override an activation rejection or plan-change barrier.
3. To attach a mandatory, enumerated reason code justifying the intervention.
4. To automatically generate an immutable `AuditLog` entry detailing actor ID, role, action, reason code, and timestamp.

---

## 2. Authorized Reason Codes
- `OVERRIDE_KYC_MANUAL`: Physical document sighted and verified in branch.
- `OVERRIDE_DEALER_SPECIAL`: Recognized bulk partner or VIP channel agreement.
- `OVERRIDE_TENURE_WAIVER`: Goodwill tenure waiver granted by retention team.
- `OVERRIDE_MNP_CLEARANCE`: Downstream manual clearance from donor operator.

---

## 3. Acceptance Criteria

### AC-09.1: CSR Activation Override
- **Given** a subscriber stuck in `PENDING_KYC` due to automated rule rejection,
- **When** an authorized CSR submits an override with `subscriber_id`, `initial_plan_id`, and `reason_code="OVERRIDE_KYC_MANUAL"`,
- **Then**:
  1. The subscriber is activated and transitions to `ACTIVE`.
  2. An immutable audit record is created containing `actor_id`, `role=Role.CSR`, `reason_code`, and timestamp.
  3. The response confirms successful activation with masked PII.

### AC-09.2: CSR Plan-Change Tenure Waiver
- **Given** an ACTIVE subscriber blocked from changing plans by minimum tenure requirements,
- **When** a CSR executes a plan-change override with `reason_code="OVERRIDE_TENURE_WAIVER"`,
- **Then**:
  1. The tenure check is bypassed.
  2. The plan change is processed.
  3. An audit log is recorded recording the tenure waiver.

### AC-09.3: Role Authorization Boundary
- **Given** a caller possessing role `SUBSCRIBER` or `DEALER`,
- **When** an override invocation is attempted,
- **Then** the request is rejected with `ERR_UNAUTHORIZED` (HTTP 403) and no state mutation occurs.
