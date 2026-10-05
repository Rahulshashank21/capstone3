# Feature Specification: Suspension & Consumption Halting (AC-06)

**Specification ID:** SPEC-SUSPENSION-01  
**Target Criteria:** AC-06, AC-02  
**Domain Area:** Subscriber Lifecycle & Provisioning Stubs  

---

## 1. Overview
A subscriber's service may be suspended either:
1. **Voluntarily**: Upon subscriber request (e.g., temporary vacation, lost SIM card).
2. **Involuntarily**: Triggered by the billing subsystem due to overdue balances or failed automated payments.

While in the `SUSPENDED` state:
- Outgoing voice calls, mobile data, and billable SMS services are halted (stubbed network consumption).
- Recurring rental charges may be prorated or paused per operational policy.
- Re-activation restores the subscriber to `ACTIVE` state, re-enables network consumption, and resumes billing.

---

## 2. Acceptance Criteria

### AC-06.1: Voluntary / Involuntary Suspension
- **Given** an ACTIVE subscriber,
- **When** suspension is triggered with reason `REQUESTED_BY_USER` or `NON_PAYMENT`,
- **Then**:
  1. The subscriber transitions from `ACTIVE` to `SUSPENDED`.
  2. The network consumption flag `is_consumption_active` is set to `False`.
  3. A state transition event is appended to audit logs.

### AC-06.2: Consumption Blocked During Suspension
- **Given** a subscriber in `SUSPENDED` state,
- **When** an incoming data session or voice event is evaluated by the consumption stub,
- **Then** the event is rejected with `ERR_CONSUMPTION_HALTED`.

### AC-06.3: Reactivation & Consumption Restoration
- **Given** a subscriber in `SUSPENDED` state,
- **When** reactivation is invoked (e.g., upon bill settlement or customer resume request),
- **Then**:
  1. Subscriber transitions from `SUSPENDED` to `ACTIVE`.
  2. Consumption flag `is_consumption_active` is restored to `True`.
  3. An audit log is recorded confirming restoration.

### AC-06.4: Invalid Transitions
- **Given** a subscriber in `PENDING_KYC` or `PORTED_OUT` state,
- **When** suspension is attempted,
- **Then** `InvalidSubscriberStateException` is raised (`ERR_INVALID_STATE_TRANSITION`).
