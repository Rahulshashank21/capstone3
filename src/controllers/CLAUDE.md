# Controller Layer Directives (src/controllers/CLAUDE.md)

## Purpose & Scope
Handles HTTP request routing, serialization/deserialization, authentication and role boundary enforcement, request correlation ID generation, and structured JSON logging.

## Core Rules
1. **Authentication Boundary (NFR-04)**: Verify caller role (`SUBSCRIBER`, `CSR`, `ADMIN`, `DEALER`) before invoking service methods.
2. **Access Control**: A subscriber role cannot view or modify subscriptions belonging to other subscriber IDs.
3. **Structured Logging (NFR-06)**: Attach `X-Correlation-ID` to all responses and log messages. Always mask subscriber IDs and phone numbers in logs.
4. **Standardized Response Envelope**:
   - Success: `{"status": "SUCCESS", "correlation_id": "...", "data": {...}}`
   - Error: `{"status": "ERROR", "correlation_id": "...", "reason_code": "ERR_...", "message": "..."}`
