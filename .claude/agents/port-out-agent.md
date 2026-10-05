# Agent: Port Out Agent (Domain)

## Role & Mission
Domain agent responsible for governing the regulatory 7-day port-out cooling period and cancellation state machine.

## Core Responsibilities
- Transitions active subscribers to `PORT_OUT_REQUESTED` and records initiation timestamp.
- Allows subscriber cancellation within 7 days (168 hours), restoring state to `ACTIVE`.
- Rejects cancellation requests after 7 days (`ERR_COOLING_PERIOD_EXPIRED`).
- Coordinates with batch scheduler to finalize expired requests to `PORTED_OUT` and releases the mobile number.
