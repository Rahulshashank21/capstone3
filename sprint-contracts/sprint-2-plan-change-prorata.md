# Sprint Contract 2: Plan Change & Pro-Rata Invariant Engine

**Sprint ID:** SPRINT-02  
**Target Acceptance Criteria:** AC-04, AC-05  
**Applicable NFRs:** NFR-01, NFR-02, NFR-08  
**Agent Roles Engaged:** `plan-change-agent`, `billing-agent`, `generator`, `evaluator`, `test-engineer`

---

## 1. Goal
Implement the plan change workflow and high-precision pro-rata billing engine for immediate prepaid upgrades, postpaid cycle migrations, and tenure enforcement. Guarantee the non-negative financial invariant $\text{charges\_total} \ge 0.00$ across all calendar boundary lengths including leap years.

## 2. Deliverables
1. `src/domain/pro_rata_calculator.py`: Fixed-point proportional allocation with itemized components.
2. `src/domain/plan_change_policy.py`: Tenure verification and migration classification.
3. `tests/unit/test_plan_change.py`: AC-04 test suite covering tenure blocking and prepaid immediacy.
4. `tests/unit/test_pro_rata_boundary.py`: AC-05 test suite verifying days 0, max, and 28/29/30/31 cycle lengths.
5. Autonomous fix loop documentation: `docs/fix-loops/fix-loop-01-prorata-rounding.md`.

## 3. Definition of Done (DoD)
- `bash .claude/hooks/pro-rata-invariant-check.sh` passes.
- All boundary tests pass with zero floating-point conversions.
- Minimum tenure violations cleanly raise `PlanChangeTenureException(ERR_MINIMUM_TENURE_NOT_MET)`.
