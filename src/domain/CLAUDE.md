# Domain Layer Directives (src/domain/CLAUDE.md)

## Purpose & Scope
This package contains pure business logic, invariants, domain entities, and state machines governing telecom subscriber operations.

## Rules & Constraints
1. **Zero External Frameworks**: No imports from `fastapi`, `starlette`, `pydantic`, `flask`, or external HTTP/database drivers.
2. **Deterministic & Pure**: Business rules must be pure functions or object methods that are completely testable in isolation.
3. **State Machine Integrity**: Any lifecycle state mutation must pass through `StateMachineValidator.validate_transition(current, target)`.
4. **Immutability Invariants**: `PlanVersion` instances marked `is_published=True` cannot be mutated.
5. **PII Protection**: Models must provide `.mask_pii()` methods to sanitize sensitive subscriber data.
