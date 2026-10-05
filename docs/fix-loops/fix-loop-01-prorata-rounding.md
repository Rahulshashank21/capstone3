# Autonomous Fix Loop 01: Pro-Rata Boundary Rounding at Leap-Year Boundary

**Incident ID:** FIX-LOOP-01  
**Detecting Agent:** `test-engineer`  
**Resolving Agent:** `billing-agent` / `generator`  
**Verifying Agent:** `evaluator`  
**Target Criterion:** AC-05, NFR-01  
**Status:** RESOLVED & MERGED  

---

## 1. Problem Detection (Observation)
During boundary fuzz testing of the pro-rata billing engine with a 29-day February leap-year cycle:
- **Scenario**: Mid-cycle migration on Day 14 of 29 from tariff \$49.99 to \$89.99.
- **Symptom**: When calculating component charges separately with premature intermediate quantization:
  $$\text{old\_component} = \text{round}\left(\frac{14}{29} \times 49.99, 2\right) = 24.133... \to 24.13$$
  $$\text{new\_component} = \text{round}\left(\frac{15}{29} \times 89.99, 2\right) = 46.546... \to 46.55$$
  $$\text{sum} = 24.13 + 46.55 = 70.68$$
  However, exact continuous proportional valuation before rounding yields:
  $$\frac{14 \times 49.99 + 15 \times 89.99}{29} = \frac{699.86 + 1349.85}{29} = \frac{2049.71}{29} = 70.679655... \to 70.68$$
  While on another boundary (\$33.33 to \$66.66 at day 10 of 29), premature component quantization created a 1-cent discrepancy between the invoice line item total and the aggregate charge, causing an audit balance mismatch in downstream billing ledgers.

---

## 2. Reproduction Test Case
The `test-engineer` agent created a dedicated reproduction test:
```python
def test_reproduce_leap_year_rounding_drift():
  old_rent = Decimal("33.33")
  new_rent = Decimal("66.66")
  cycle_days = 29
  days_used = 10

  # Prior naive approach summed independently rounded components
  # Desired behavior: Calculate unrounded total in Decimal, then quantize with ROUND_HALF_UP
  res = ProRataCalculator.calculate(old_rent, new_rent, days_used, cycle_days)
  assert res == Decimal("55.17")
```

---

## 3. Autonomous Root Cause Analysis & Fix
1. **Root Cause**: Premature intermediate quantization of individual component fractions before final summation accumulated half-cent rounding errors.
2. **Remediation**:
   - Compute components in full-precision `Decimal` arithmetic.
   - Aggregate unrounded components into `unrounded_total`.
   - Apply `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` to the final total.
   - Itemize old and new components consistently such that `total_charge` is guaranteed mathematically sound.
3. **Guardrail Added**:
   - Encoded the invariant check into `.claude/hooks/pro-rata-invariant-check.sh` and parametrized test across all cycle lengths (28, 29, 30, 31).

---

## 4. Verification & Ratification
- Ran `pytest tests/unit/test_pro_rata_boundary.py`: All passed.
- Ran `bash .claude/hooks/pro-rata-invariant-check.sh`: `[PASS] Pro-rata charge invariant verified successfully.`
- Evaluation approved without human intervention.
