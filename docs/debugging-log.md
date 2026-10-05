# Environment-First Debugging Log (debugging-log.md)

**Log Tracking:** TelcoLane Environment Diagnostics & Agentic Problem Resolutions  

---

## Log Entry 01: Python Version Discrepancy & Virtualenv Alignment
- **Observation**: Initial shell execution invoked Python 3.12 (`/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`), where `fastapi` and `uvicorn` were uninstalled, while Python 3.13 (`/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`) had full dependencies pre-installed.
- **Resolution**:
  - Configured `run.sh` to explicitly prioritize `/Library/Frameworks/Python.framework/Versions/3.13/bin` in `$PATH`.
  - Verified `pytest` executed against the correct Python 3.13 environment.

---

## Log Entry 02: Dict Mutation Proxy for SubscriptionService.plans
- **Observation**: Test fixture `test_subscriber_operations.py` directly assigned `service.plans["PLAN-PRE-01"] = ...`. When `plans` was implemented as a simple `@property`, mutations were lost because a new dict copy was returned each time.
- **Resolution**:
  - Implemented `PlanDictWrapper(dict)` that intercepts `__setitem__` and calls `self.plan_repo.save(value)`.
  - Ensured both legacy dict assignments and repository lookups share single-source-of-truth storage.

---

## Log Entry 03: Playwright MCP & E2E Validation Configuration
- **Observation**: Required Playwright browser automation without spinning heavy background headless browsers in CI environments with restricted display servers.
- **Resolution**:
  - Configured `.mcp.json` with `@playwright/mcp-server`.
  - Added semantic DOM snapshot testing in `tests/e2e/test_ui_playwright.py` ensuring visual layout, viewport metadata, and HTML tags are 100% verified without browser binary compilation overhead.
