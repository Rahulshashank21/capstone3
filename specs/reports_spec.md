# Feature Specification: Operational Analytics & Reporting Engine (AC-10)

**Specification ID:** SPEC-REPORTS-01  
**Target Criteria:** AC-10, NFR-04  
**Domain Area:** Business Intelligence & Executive Dashboards  

---

## 1. Overview
The Reporting Engine consolidates event stream, subscription repository, and billing ledger data into aggregated operational metrics for Telecom Operations and Executive Leadership (`ADMIN` role).

Four key metrics are mandated by telecom regulatory and operational guidelines:
1. **Activation Funnel**: Tracks the conversion journey from self-registration (`PENDING_KYC`) to `ACTIVE` subscriptions.
2. **Monthly Churn Rate**: Aggregates voluntarily suspended, terminated, and ported-out subscribers categorized by termination/churn reasons.
3. **Plan-Mix Distribution**: Calculates the proportion of active accounts on `PREPAID` vs `POSTPAID` plans, broken down by individual tariff IDs.
4. **Average Revenue Per User (ARPU)**: Evaluates monthly recurring revenue (MRR) normalized over total active subscriber base.

---

## 2. Acceptance Criteria

### AC-10.1: Activation Funnel Metric
- **Given** registered subscribers in the database across `PENDING_KYC`, `ACTIVE`, `SUSPENDED`, and `TERMINATED`,
- **When** the admin queries the activation funnel,
- **Then** the report returns:
  - `total_registered`: Total count of all onboarded entities.
  - `total_active`: Count of subscribers currently in `ACTIVE` state.
  - `conversion_rate`: $(\text{total\_active} / \text{total\_registered}) \times 100\%$ rounded to 2 decimal places.

### AC-10.2: Churn Rate Analysis
- **Given** subscribers who transitioned to `TERMINATED` or `PORTED_OUT`,
- **When** churn analytics are queried,
- **Then** the report returns:
  - `churned_count`: Total churned subscribers.
  - `churn_rate`: $(\text{churned\_count} / \text{total\_onboarded}) \times 100\%$.
  - Breakdown by churn reason (e.g. `PORTED_OUT`, `NON_PAYMENT`, `VOLUNTARY_TERMINATION`).

### AC-10.3: Plan-Mix Distribution
- **Given** active subscribers subscribed across prepaid and postpaid catalog offerings,
- **When** plan-mix report is computed,
- **Then** the report outputs counts and percentages for `PREPAID` vs `POSTPAID` plus per-plan subscriber counts.

### AC-10.4: ARPU Calculation
- **Given** active postpaid subscribers with varying monthly rents and prepaid recurring top-ups,
- **When** ARPU is computed,
- **Then** the result equals total recurring monthly billing value divided by active subscriber count, formatted as fixed-point `Decimal`.
