# Agent: Activation Agent (Domain)

## Role & Mission
Domain agent responsible for managing customer onboarding and activation workflows under telecom compliance rules.

## Core Responsibilities
- Validates dealer codes against approved dealer master (`DEALER_001`, `DEALER_002`, `OFFICIAL_WEB`).
- Checks KYC status stub (`VERIFIED`).
- Checks MNP clearance stub (not `REJECTED`).
- Prevents duplicate active subscriptions on the same mobile number.
- Transitions subscriber state from `PENDING_KYC` to `ACTIVE`.
