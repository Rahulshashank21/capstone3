# Feature Specification: Plan Change & Pro-Rata Billing (AC-04, AC-05)

**Specification ID:** SPEC-PLAN-CHANGE-01  
**Target Criteria:** AC-04, AC-05, NFR-01, NFR-08  
**Domain Area:** Plan Lifecycle & Financial Engine  

---

## 1. Overview
Subscribers may upgrade or downgrade their tariff plans based on usage requirements:
- **Prepaid Plans**: Change is effective immediately upon application. Validity days reset or extend according to plan rules.
- **Postpaid Plans**: By default, recurring plans transition on the next monthly billing cycle boundary. When an immediate mid-cycle migration occurs, the system calculates an accurate pro-rata bill.
- **Tenure Enforcement**: A plan may configure a `min_tenure_days` rule. Subscribers attempting to migrate before fulfilling the required tenure are blocked unless granted a CSR override.

---

## 2. Mathematical Definition: Pro-Rata Invariant (AC-05, NFR-01)
For a mid-cycle change on cycle day $D_{used}$ within total cycle days $D_{cycle}$:
$$\text{old\_charge} = \left(\frac{D_{used}}{D_{cycle}}\right) \times R_{old}$$
$$\text{new\_charge} = \left(\frac{D_{cycle} - D_{used}}{D_{cycle}}\right) \times R_{new}$$
$$\text{charges\_total} = \text{round}_{half\_up}(\text{old\_charge} + \text{new\_charge}, 2)$$

### Key Mathematical Invariants:
1. **Financial Precision**: All operands and intermediate steps must use `Decimal`. Floating-point math is strictly prohibited.
2. **Non-Negative Invariant**: $\text{charges\_total} \ge 0.00$. If a downgrade would mathematically result in a negative invoice, the platform quantizes the bill to zero or records an explicit credit ledger without violating the non-negative invoice constraint.
3. **Boundary Day Invariants**:
   - At $D_{used} = 0$: $\text{charges\_total} = R_{new}$ (100% on new plan).
   - At $D_{used} = D_{cycle}$: $\text{charges\_total} = R_{old}$ (100% on old plan).
   - At $0 < D_{used} < D_{cycle}$: Strictly weighted combination.

---

## 3. Acceptance Criteria

### AC-04.1: Prepaid Immediate Plan Upgrade
- **Given** an ACTIVE subscriber on a PREPAID plan,
- **When** the subscriber chooses a new PREPAID plan,
- **Then** the plan change takes effect immediately, `current_plan_id` is updated, and the new validity period begins.

### AC-04.2: Minimum Tenure Enforcement
- **Given** an ACTIVE subscriber whose current plan has `min_tenure_days = 90`,
- **When** the subscriber attempts to change plans after only 15 days,
- **Then** the request is rejected with `DomainException("ERR_MINIMUM_TENURE_NOT_MET")`.

### AC-05.1: Mid-Cycle Postpaid Pro-Rata Billing
- **Given** an ACTIVE subscriber on `PLAN-POST-01` (rent \$50.00) changing to `PLAN-POST-02` (rent \$100.00) on day 10 of a 30-day billing cycle,
- **When** pro-rata calculation is evaluated:
  - Old charge: $\frac{10}{30} \times 50.00 = 16.6666...$
  - New charge: $\frac{20}{30} \times 100.00 = 66.6666...$
  - Total: $83.3333... \to \text{Decimal}("83.33")$
- **Then** `charges_total` equals `Decimal("83.33")` and a billing record is persisted.

### AC-05.2: Boundary Date Safety & Leap Year Handling
- **Given** a 29-day billing cycle in February of a leap year or a 31-day month,
- **When** pro-rata is calculated across cycle days $0$, $1$, $D_{mid}$, and $D_{max}$,
- **Then** every calculated charge satisfies `charge >= Decimal("0.00")` with zero floating point drift.
