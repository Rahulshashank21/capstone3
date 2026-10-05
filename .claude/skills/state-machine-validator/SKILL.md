---
name: state-machine-validator
description: Technical skill to verify legal state transitions and assert subscriber lifecycle correctness.
---

# State Machine Validator Skill

## Purpose
Guarantees formal subscriber lifecycle correctness across asynchronous events, webhooks, and REST invocations.

## Transition Graph & Rules
```
PENDING_KYC ----> ACTIVE ----> SUSPENDED ----> ACTIVE
     |              |              |
     |              v              v
     +-------> TERMINATED <--------+
                    ^
                    |
           PORT_OUT_REQUESTED
              /           \
             v             v
          ACTIVE       PORTED_OUT
```
All transitions outside this graph raise `InvalidSubscriberStateException(ERR_INVALID_STATE_TRANSITION)`.
