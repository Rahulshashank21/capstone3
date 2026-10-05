---
name: port-out-cooling-checker
description: Manages the regulatory 7-day port-out cooling period and cancellation eligibility.
---

# Port-Out Cooling Checker Skill

## Operational Rules
1. **Cooling Window Duration**: Exactly 7 days (7 * 24 hours = 168 hours = 604,800 seconds).
2. **Cancellation Logic**:
   - If `current_time - port_out_requested_at <= 7 days`:
     - Cancellation is PERMITTED.
     - State transitions back to `ACTIVE`.
     - Timestamp `port_out_requested_at` is cleared.
   - If `current_time - port_out_requested_at > 7 days`:
     - Cancellation is FORBIDDEN (`ERR_COOLING_PERIOD_EXPIRED`).
     - State should transition to `PORTED_OUT` upon execution of completion job.
