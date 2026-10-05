---
name: pro-rata-calculator
description: Computes high-precision fixed-point pro-rata charges for mid-cycle postpaid migrations and enforces mathematical invariants.
---

# Pro-Rata Calculator Skill

## Mathematical Specification
For a mid-cycle plan change occurring on day $D_{used}$ of cycle $D_{cycle}$:
$$\text{old\_charge} = \left(\frac{D_{used}}{D_{cycle}}\right) \times R_{old}$$
$$\text{new\_charge} = \left(\frac{D_{cycle} - D_{used}}{D_{cycle}}\right) \times R_{new}$$
$$\text{total} = \text{ROUND\_HALF\_UP}(\text{old\_charge} + \text{new\_charge}, 2)$$

## Mandated Invariants
1. **Never Float**: All inputs and outputs must be instances of `decimal.Decimal`.
2. **Non-Negative Invariant**: $\text{total} \ge 0.00$. Any computation yielding a negative charge must raise `ProRataCalculationException("ERR_NEGATIVE_PRO_RATA")`.
3. **Cycle Boundary Constraints**:
   - $0 \le D_{used} \le D_{cycle}$
   - $D_{cycle} > 0$
4. **Rounding Policy**: Quantize to `Decimal("0.01")` using `ROUND_HALF_UP`.
