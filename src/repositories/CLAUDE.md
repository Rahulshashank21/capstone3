# Repository Layer Directives (src/repositories/CLAUDE.md)

## Purpose & Scope
Provides persistent storage abstractions for domain entities including Subscribers, PlanVersions, BillingRecords, and AuditLogs.

## Core Rules
1. **Append-Only Principle (NFR-02, NFR-05)**: Never delete or overwrite historical published plans or audit events.
2. **Data Consistency**: Maintain index lookups by `subscriber_id` and `mobile_number` safely with thread synchronization.
3. **Decoupling**: Domain models must not know about storage implementations (in-memory or relational).
