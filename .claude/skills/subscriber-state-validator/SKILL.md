---
name: subscriber-state-validator
description: Validates subscriber lifecycle state transitions and prevents illegal out-of-order mutations.
---

# Subscriber State Validator Skill

## State Transition Matrix
| Current State | Permitted Next States |
| :--- | :--- |
| `PENDING_KYC` | `ACTIVE`, `TERMINATED` |
| `ACTIVE` | `SUSPENDED`, `PORT_OUT_REQUESTED`, `TERMINATED` |
| `SUSPENDED` | `ACTIVE`, `TERMINATED` |
| `PORT_OUT_REQUESTED` | `ACTIVE` (Cancelled), `PORTED_OUT` (Finalized), `TERMINATED` |
| `PORTED_OUT` | (Terminal) |
| `TERMINATED` | (Terminal) |

## Invariants
- Any transition not in the matrix must raise `InvalidSubscriberStateException` with code `ERR_INVALID_STATE_TRANSITION`.
- No duplicate active subscriptions allowed for the same mobile number (`ERR_DUPLICATE_ACTIVE_NUMBER`).
