# TelcoLane: Subscriber & Plan Lifecycle Operations Platform
## Business Case Document (BC-AINE-020)

---

## 1. Executive Summary & Problem Formulation
Next-generation telecommunications operators face severe operational friction arising from fragmented legacy BSS/OSS stacks. In conventional telecom environments, subscriber registration, KYC document verification, tariff plan migrations, billing engines, and regulatory churn workflows (such as Mobile Number Portability) operate as disconnected silos.

This fragmentation produces critical business vulnerabilities:
1. **Financial Discrepancies in Mid-Cycle Billing**: Inaccurate pro-rata calculations or floating-point rounding drift trigger widespread customer billing disputes, invoice recalculations, and regulatory fines.
2. **Regulatory Non-Compliance in MNP Cooling Periods**: Strict telecommunication directives mandate a 7-day cooling period during which subscribers can reverse port-out requests. Fragmented state machines risk premature disconnection.
3. **Identity & PII Data Vulnerability**: Inadequate masking of Aadhaar numbers, PAN records, and raw phone numbers in application logs creates severe privacy liabilities under modern data protection regimes.
4. **Unregulated Plan Alterations**: In-place mutations to tariff catalogs violate customer billing contracts and invalidate historical audit records.

**The Solution: TelcoLane**  
TelcoLane is a unified, AI-native subscriber and plan lifecycle operations substrate that consolidates onboarding, tariff catalog management, high-precision pro-rata billing, suspension/reactivation, and regulatory port-out compliance into an immutable, rule-driven platform.

---

## 2. Target Personas & Stakeholders
| Persona | Context & Workflows | Core Needs & Capabilities |
| :--- | :--- | :--- |
| **Subscriber (End User)** | Prospective or active retail customer accessing web or mobile self-service. | Self-registration, transparent PII protection, immediate plan upgrades, transparent pro-rata preview before checkout, temporary vacation suspension, and port-out cooling period control. |
| **Certified Dealer / Point of Sale** | Physical store agent or authorized online affiliate onboarding subscribers. | Fast verification against authorized dealer registry (`DEALER_001`, `DEALER_002`, `OFFICIAL_WEB`), seamless SIM activation, and instant feedback on KYC clearance. |
| **Customer Service Representative (CSR)** | Operational support agent handling customer exceptions, failed verifications, or dispute queues. | CSR Workbench with automated exception queue, authority to grant manual overrides with mandatory reason codes, and instant inspection of historical audit trails. |
| **Telecom Administrator / Operations Lead** | Business executive monitoring operational health, network revenue, and subscriber churn. | Executive analytics dashboard displaying real-time activation funnels, churn categorization, plan-mix distribution, and Average Revenue Per User (ARPU). |

---

## 3. Success Metrics & Business KPIs
The TelcoLane platform is evaluated against five key quantifiable business indicators:
1. **Time-to-Activation (TTA)**: Rapid, automated rule verification (KYC stub, dealer authorization, MNP validation, active number exclusivity) reducing customer onboarding from hours to sub-second transactions.
2. **Zero Billing Dispute Rate (NFR-01)**: 100% adherence to fixed-point `Decimal` math with `ROUND_HALF_UP` precision. Zero floating-point calculation drift across all calendar cycle lengths (28, 29 leap year, 30, and 31 days).
3. **100% Port-Out Cooling Compliance (AC-07)**: Strict enforcement of the 168-hour (7-day) cooling window, ensuring zero accidental subscriber terminations before statutory cooling expiration.
4. **Zero Plaintext PII Leakage (NFR-03)**: 100% masking of phone numbers (`XXXXXX1234`) and redaction of national identity references (`[REDACTED]`) in all logs, API responses, and external views.
5. **Operational State Machine Rigor (NFR-08)**: Zero illegal subscriber lifecycle jumps and complete prevention of duplicate active numbers on the network.

---

## 4. Telecom Domain Business Rules
The platform establishes four foundational operational policies:

### 4.1 Activation Rules (AC-01, AC-08)
- Self-registration creates entities strictly in `PENDING_KYC` state.
- Transition to `ACTIVE` requires:
  - Identity verification stub evaluated to `VERIFIED`.
  - Onboarding dealer whitelisted in approved registry.
  - MNP clearinghouse status not `REJECTED`.
  - Mobile number not currently `ACTIVE` in another subscription.

### 4.2 Tariff Plan Management & Immutability (AC-03)
- Supports `PREPAID` (validity in calendar days, quota in GB) and `POSTPAID` (monthly recurring billing cycles).
- Published plan versions (`is_published=True`) are sealed and immutable. Updates require publishing a new sequential version (`version = version + 1`).

### 4.3 Pro-Rata Billing & Invariant Math (AC-04, AC-05)
- Mid-cycle migrations compute proportional charges:
  $$\text{charges\_total} = \left(\frac{D_{used}}{D_{cycle}} \times R_{old}\right) + \left(\frac{D_{cycle} - D_{used}}{D_{cycle}} \times R_{new}\right)$$
- The invoice invariant $\text{charges\_total} \ge 0.00$ must strictly hold under all boundary conditions.
- Plan `min_tenure_days` is enforced prior to migration unless waived by authorized CSR override.

### 4.4 Regulatory Port-Out & Cooling Period (AC-07)
- Request transitions subscription to `PORT_OUT_REQUESTED`.
- 7-day cooling timer is started. Cancellation within 7 days unconditionally restores subscription to `ACTIVE`.
- Expired requests are finalized to `PORTED_OUT`, terminating service and freeing active number inventory.

---

## 5. Value Proposition & Competitive Differentiation
1. **AI-Native Engineering Substrate**: The entire platform was designed, scaffolded, generated, and verified through Claude Code autonomous agents operating under strict specifications.
2. **Financial Determinism**: By replacing error-prone manual tariff coding with fixed-point domain invariant solvers, TelcoLane eliminates revenue leakage.
3. **Auditability & Regulatory Defense**: Every operational mutation, override, and state transition is captured in an append-only, tamper-evident audit ledger.
4. **Turnkey Local Deployment**: Self-contained architecture deployable locally with a single command, accompanied by seed data, automated test suites, and responsive frontend interfaces.
