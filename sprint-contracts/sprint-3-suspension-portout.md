# Sprint Contract 3: Suspension & Port-Out Cooling Period State Machine

**Sprint ID:** SPRINT-03  
**Target Acceptance Criteria:** AC-06, AC-07  
**Applicable NFRs:** NFR-02, NFR-04, NFR-08  
**Agent Roles Engaged:** `port-out-agent`, `state-machine-validator`, `generator`, `evaluator`, `test-engineer`

---

## 1. Goal
Implement subscriber suspension/reactivation lifecycle with network consumption halting (stubbed), and the 7-day regulatory port-out cooling period state machine with cancellation and finalization logic.

## 2. Deliverables
1. `src/domain/suspension_policy.py`: Suspension reasons, consumption gating, and reactivation restoration.
2. `src/domain/port_out_policy.py`: 7-day cooling period validation, cancellation window, and terminal finalization.
3. `tests/unit/test_suspension.py`: AC-06 test cases verifying consumption halting.
4. `tests/unit/test_port_out.py`: AC-07 test cases verifying 7-day cooling cancellation and expiry.
5. Autonomous fix loop documentation: `docs/fix-loops/fix-loop-02-suspension-consumption.md`.

## 3. Definition of Done (DoD)
- `tests/unit/test_suspension.py` and `tests/unit/test_port_out.py` pass.
- Inactive / suspended consumption attempts raise `ERR_CONSUMPTION_HALTED`.
- Port-out cancellations after 7 days raise `ERR_COOLING_PERIOD_EXPIRED`.
- Finalized port-outs release active mobile numbers from the active set.
