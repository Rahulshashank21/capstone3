# Service Layer Directives (src/services/CLAUDE.md)

## Purpose & Scope
Orchestrates application use cases, connects repositories with domain models, enforces transaction boundaries, and records immutable audit trails.

## Responsibilities
1. **Coordination**: Coordinate domain rules with repository queries/persistence.
2. **Audit Logging**: Every mutation (activation, override, plan change, port-out, suspension) must generate an `AuditLog` entry in the `AuditLogRepository`.
3. **Thread Safety**: Ensure multi-step operations (e.g. reserving active numbers, deducting balances) are thread-safe and idempotent.
4. **Error Handling**: Catch domain exceptions, wrap them with operational context if necessary, or pass through to controllers.
