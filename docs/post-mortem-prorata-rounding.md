# Post-Mortem: Pro-Rata Boundary Invariant & Floating-Point Drift

**Incident ID:** PM-2026-001  
**Severity:** High (Financial Invariant Breach Risk)  
**Date:** 2026-10-05  
**Authors:** AI-Native Engineering Substrate (`planner`, `billing-agent`, `evaluator`)  
**Status:** Closed & Permanently Mitigated  

---

## 1. Summary
During stress-testing of mid-cycle postpaid migrations, automated fuzzing detected potential rounding drift on 29-day leap year billing cycles when using Python's native binary floating-point representation (`float`). In extreme boundary combinations, floating-point subtraction produced negative epsilon values (`-0.000000000000001`), threatening the core financial invariant $\text{charges\_total} \ge 0.00$.

---

## 2. Root Cause Analysis
1. **IEEE 754 Representation Limits**: Binary floating-point arithmetic cannot represent decimal fractions like 0.1 or 0.01 with exact precision.
2. **Intermediate Rounding**: Rounding intermediate steps prematurely introduced cumulative 1-cent reconciliation errors.
3. **Environment Isolation**: Early script prototypes invoked `/usr/bin/python3` which lacked fixed-point test scaffolding.

---

## 3. Corrective Actions Taken (Environment-First Resolution)
1. **Strict Type Invariant**: Enforced `decimal.Decimal` with `ROUND_HALF_UP` across the entire domain layer (`src/domain/pro_rata_calculator.py`).
2. **Automated Hook Installation**: Created `.claude/hooks/pro-rata-invariant-check.sh` and added it to CI pipeline.
3. **Architecture Testing**: Added `test_no_floating_point_casts_in_domain_rules()` in `tests/architecture/test_layering.py` to statically verify no `float()` casts exist in domain logic.
4. **Autonomous Fix Loop Record**: Documented in `docs/fix-loops/fix-loop-01-prorata-rounding.md`.
