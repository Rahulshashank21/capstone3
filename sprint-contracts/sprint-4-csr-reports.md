# Sprint Contract 4: CSR Overrides, Reports, UI & CI/CD Pipeline

**Sprint ID:** SPRINT-04  
**Target Acceptance Criteria:** AC-09, AC-10, NFR-01 to NFR-08  
**Applicable NFRs:** NFR-01, NFR-02, NFR-03, NFR-04, NFR-05, NFR-06, NFR-07, NFR-08  
**Agent Roles Engaged:** `csr-override-agent`, `billing-agent`, `ui-designer`, `design-critic`, `evaluator`, `test-engineer`

---

## 1. Goal
Complete the subscriber lifecycle platform by implementing the CSR Workbench with authorized manual overrides and audit trail, the operational reports engine (activation funnel, churn rate, plan-mix distribution, ARPU), the FastAPI backend server with `/health`, the responsive React frontend portal, Playwright UI snapshot validation, and the CI/CD pipeline with Claude Code Action.

## 2. Deliverables
1. `src/domain/csr_override_policy.py`: Enforces authorized roles and whitelisted reason codes.
2. `src/services/reporting_service.py`: Computes activation funnel, churn metrics, plan mix, and ARPU in fixed-point `Decimal`.
3. `src/controllers/api_controller.py`: Comprehensive REST controller with PII masking and correlation IDs.
4. `src/main.py`: FastAPI server with `/health` SLA (< 1.0s), CORS, and OpenAPI docs.
5. `src/seed.py`: Pre-populates catalog, subscribers across states, and audit trails.
6. `frontend/src/App.jsx` & `App.css`: Responsive 5-tab telecom operations portal.
7. `tests/e2e/test_ui_playwright.py`: DOM and UI snapshot testing under `tests/e2e/snapshots/`.
8. `scripts/run_agent_pipeline.py`: Programmatic Claude Agent SDK workflow orchestrator.
9. CI pipelines: `.gitlab-ci.yml` and `.github/workflows/ci.yml`.
10. `coverage.xml`: Committed Cobertura coverage artifact (> 90%).

## 3. Definition of Done (DoD)
- `/health` responds with HTTP 200 in < 1 second.
- All 10 ACs (AC-01 to AC-10) and all 8 NFRs verified by automated tests.
- Zero unmasked PII logged.
- Coverage artifact generated and committed.
