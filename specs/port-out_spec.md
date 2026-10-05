# Feature Specification: Port-Out Cooling-Period State Machine (AC-07)

**Specification ID:** SPEC-PORT-OUT-01  
**Target Criteria:** AC-07, AC-02, NFR-02  
**Domain Area:** Regulatory Compliance & Churn Workflows  

---

## 1. Overview
Under national telecommunications regulatory directives (e.g., MNP Porting Regulations), when a customer requests to port their mobile number to a competing recipient operator:
1. The subscription enters a mandatory **7-day cooling period** (168 hours).
2. The state transitions to `PORT_OUT_REQUESTED`.
3. Within the 7-day window, the subscriber retains the legal right to change their mind and cancel the port-out request, immediately returning to `ACTIVE` state with uninterrupted service.
4. If the 7 days elapse without cancellation, the recipient network finalizes the donor operator release, transitioning the subscription to `PORTED_OUT` (terminal state), freeing active number tracking.

---

## 2. Acceptance Criteria

### AC-07.1: Initiation of Port-Out & Cooling Period
- **Given** an ACTIVE subscriber,
- **When** the subscriber initiates a port-out request (with optional recipient operator code),
- **Then**:
  1. The subscriber transitions from `ACTIVE` to `PORT_OUT_REQUESTED`.
  2. `port_out_requested_at` is stamped with the current UTC timestamp.
  3. A port-out request record is appended to the regulatory audit log.

### AC-07.2: Cancellation Within 7-Day Window
- **Given** a subscriber in `PORT_OUT_REQUESTED` state with elapsed time $< 7$ days (e.g., 3 days),
- **When** the subscriber submits a cancellation request,
- **Then**:
  1. The port-out request is cancelled.
  2. The subscriber transitions back to `ACTIVE` state.
  3. `port_out_requested_at` is cleared (or archived in history).
  4. An audit log is recorded: `PORT_OUT_CANCELLED`.

### AC-07.3: Cooling Period Expiry & Finalization
- **Given** a subscriber in `PORT_OUT_REQUESTED` whose `port_out_requested_at` is $> 7$ days ago,
- **When** cancellation is attempted,
- **Then** the request is rejected with `ERR_COOLING_PERIOD_EXPIRED`.
- **When** the port-out completion job executes,
- **Then**:
  1. Subscriber transitions to `PORTED_OUT`.
  2. The mobile number is released from active operator numbers.
  3. No further state transitions can occur from `PORTED_OUT`.

---

## 3. State Invariants
- Direct transition from `PENDING_KYC` to `PORT_OUT_REQUESTED` is forbidden (`ERR_INVALID_STATE_TRANSITION`).
- A ported-out subscriber cannot be reactivated; a new registration is required.
