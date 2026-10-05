# Test-Driven Development (TDD) Discipline & Evidence (tdd.md)

**Project:** TelcoLane Subscriber & Plan Lifecycle Operations  
**Methodology:** Red — Green — Refactor  
**Status:** 100% Test Automation Verified  

---

## 1. TDD Philosophy & Discipline
In an AI-native engineering environment, human engineers act as quality gatekeepers who define specifications and test criteria *before* implementation code is generated. All features in TelcoLane followed strict Test-Driven Development:
1. **Red Phase**: Define acceptance criteria in `specs/*_spec.md` and write failing tests tagged with `AC-NN` identifiers. Run tests to confirm assertion failures.
2. **Green Phase**: Instruct `generator` agents to synthesize the minimum necessary domain models, policies, and service methods to make the tests pass.
3. **Refactor Phase**: Optimize algorithm clarity, extract invariant checks into dedicated policy modules, enforce strict `Decimal` precision, and verify layering rules.

---

## 2. Worked Example: AC-05 Pro-Rata Boundary-Date Test

### 2.1 The Requirement
When an active postpaid subscriber migrates to a higher tariff mid-cycle, the system must compute a weighted pro-rata bill using fixed-point arithmetic, satisfying the invariant $\text{charges\_total} \ge 0.00$ even across boundary cycle lengths (28, 29, 30, and 31 days).

### 2.2 Red Phase (Failing Test)
The `test-engineer` wrote the boundary test in `tests/unit/test_pro_rata_boundary.py`:
```python
def test_ac_05_pro_rata_boundary_day_zero():
  """AC-05: Day 0 transition means entire cycle charged at new rate."""
  old_rent = Decimal("50.00")
  new_rent = Decimal("100.00")
  result = ProRataCalculator.calculate(
      old_rent, new_rent, days_used=0, cycle_days=30
  )
  assert result == Decimal("100.00")
```
*Initial Run Output:*
`ImportError: cannot import name 'ProRataCalculator' from 'src.domain.rules'` (Red)

### 2.3 Green Phase (Minimum Viable Implementation)
The `generator` implemented the proportional calculation:
```python
class ProRataCalculator:

  @staticmethod
  def calculate(
      old_rent: Decimal, new_rent: Decimal, days_used: int, cycle_days: int
  ) -> Decimal:
    days_used_dec = Decimal(str(days_used))
    cycle_days_dec = Decimal(str(cycle_days))
    days_remaining = cycle_days_dec - days_used_dec

    old_c = (days_used_dec / cycle_days_dec) * old_rent
    new_c = (days_remaining / cycle_days_dec) * new_rent
    return (old_c + new_c).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```
*Test Run Output:* `test_ac_05_pro_rata_boundary_day_zero PASSED` (Green)

### 2.4 Refactor Phase (Hardening Invariants & Architecture)
The implementation was refactored into `src/domain/pro_rata_calculator.py`:
- Added input validation for negative days and zero cycle days.
- Added non-negative invariant assertion: `assert total_charge >= Decimal("0.00")`.
- Separated itemized breakdown (`calculate_itemized`) to support transparent billing itemization.
- Parameterized tests across 28, 29 (leap year), 30, and 31 day billing periods.
- Installed verification hook `.claude/hooks/pro-rata-invariant-check.sh` to prevent regressions.

---

## 3. Test Suites Across Repository
The repository maintains 13 discrete test files:
1. `tests/architecture/test_arch.py` (Domain isolation check)
2. `tests/architecture/test_layering.py` (Controller-Service-Repo boundary checks)
3. `tests/unit/test_subscriber_operations.py` (Legacy regression suite)
4. `tests/unit/test_activation.py` (AC-01, AC-08)
5. `tests/unit/test_plan_catalog.py` (AC-03)
6. `tests/unit/test_plan_change.py` (AC-04)
7. `tests/unit/test_pro_rata_boundary.py` (AC-05)
8. `tests/unit/test_suspension.py` (AC-06)
9. `tests/unit/test_port_out.py` (AC-07)
10. `tests/unit/test_csr_override.py` (AC-09)
11. `tests/unit/test_reports.py` (AC-10)
12. `tests/unit/test_state_machine.py` (AC-02)
13. `tests/unit/test_api_controller.py` (NFR-04, NFR-06, NFR-07)
14. `tests/e2e/test_ui_playwright.py` (UI DOM Snapshot validation)
