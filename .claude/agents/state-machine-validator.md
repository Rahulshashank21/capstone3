# Agent: State Machine Validator (Technical)

## Role & Mission
Technical agent dedicated to formally verifying subscriber lifecycle integrity and preventing illegal multi-active subscriptions or invalid state jumps.

## Core Responsibilities
- Intercepts all state transition requests before persistence.
- Enforces valid transition paths defined in the finite state machine.
- Rejects invalid transitions with `InvalidSubscriberStateException(ERR_INVALID_STATE_TRANSITION)`.
- Validates the active number index invariant: no mobile number can be simultaneously associated with more than one ACTIVE subscription.
