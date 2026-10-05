# Agent Registry & Capabilities Index

| Agent Name | Scope | Key Responsibility |
| :--- | :--- | :--- |
| `activation-agent` | Domain | Validates dealer code, KYC stub, MNP status, and transitions subscriber to ACTIVE state |
| `plan-change-agent` | Domain | Computes pro-rata postpaid bills and immediate prepaid upgrades |
| `port-out-agent` | Domain | Controls the 7-day cooling-period state machine and cancellation flows |
| `state-machine-validator` | Technical | Verifies legal state transitions and prevents illegal multi-active subscriptions |
