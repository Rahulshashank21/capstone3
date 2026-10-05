# Backend Source Layer Guidelines (src/CLAUDE.md)

## Architectural Role
The `src/` directory contains all backend implementation code for the TelcoLane platform. It is structured into strict architectural layers:
- `domain/`: Business entities, state machine validator, calculation engines, and domain exception definitions.
- `repositories/`: Thread-safe persistence abstractions and append-only ledgers.
- `services/`: Business workflow orchestrators, transaction coordinators, and audit writers.
- `controllers/`: HTTP REST endpoints, role authentication boundaries, and correlation ID handling.

## Core Mandates
1. **Layer Dependency Flow**:
   - `controllers` -> `services` -> `repositories` -> `domain`
   - `domain` MUST NEVER import from `services`, `controllers`, or external web frameworks.
2. **Financial Precision**: All calculations involving money (rents, pro-rata, top-ups) must use Python's `Decimal` type from standard library with `ROUND_HALF_UP`. Never use `float`.
3. **PII Masking**: Ensure any logging in services and controllers passes data through `mask_pii()` before formatting strings or outputting JSON.
4. **Exceptions**: Domain exceptions must subclass `DomainException` and define explicit, machine-readable `reason_code` strings.
