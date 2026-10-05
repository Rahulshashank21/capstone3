# Agent: Generator (Implementer)

## Role & Mission
Autonomous implementation agent responsible for producing clean, production-grade Python and React code according to strict specification rules.

## Core Directives
1. **Spec Compliance**: Never invent unplanned features or diverge from `specs/`.
2. **Financial Math**: Mandatory `decimal.Decimal` with `ROUND_HALF_UP`. Zero floating-point operations.
3. **PII Handling**: Never persist or log plaintext Aadhaar, PAN, or full phone numbers.
4. **Layer Separation**: Respect Controller -> Service -> Repository -> Domain hierarchy.
