# Sprint Contract 1: Foundation, Catalog & Activation Substrate

**Sprint ID:** SPRINT-01  
**Target Acceptance Criteria:** AC-01, AC-02, AC-03, AC-08  
**Applicable NFRs:** NFR-01, NFR-02, NFR-03, NFR-04, NFR-05, NFR-08  
**Agent Roles Engaged:** `planner`, `generator`, `evaluator`, `activation-agent`, `test-engineer`, `state-machine-validator`

---

## 1. Goal
Establish the AI-native substrate, layered `CLAUDE.md` architecture, core specifications, domain models, finite state machine validator, append-only repositories, and complete implementation for plan catalog and rule-driven subscriber self-registration and activation.

## 2. Deliverables
1. **Core Specs**: `specs/app_spec.md`, `specs/plan-catalog_spec.md`, `specs/activation_spec.md`.
2. **Layered Guidelines**: Root `CLAUDE.md`, `AGENTS.md`, and per-folder `CLAUDE.md` files.
3. **Agent Substrate**: Base agents + domain agents (`activation-agent`, `plan-change-agent`, `port-out-agent`, `billing-agent`, `csr-override-agent`, `state-machine-validator`) + bonus agents.
4. **Skills & Hooks**: 7 project skills in `.claude/skills/`, 4 custom commands in `.claude/commands/`, 4 automated verification hooks in `.claude/hooks/`.
5. **Domain & Repositories**:
   - `src/domain/models.py`, `src/domain/state_machine.py`, `src/domain/activation_policy.py`, `src/domain/plan_policy.py`.
   - `SubscriberRepository`, `PlanRepository`, `AuditRepository`, `BillingRepository`.
6. **Tests**: Tagged unit tests covering AC-01, AC-02, AC-03, AC-08, and structural architecture tests.

## 3. Definition of Done (DoD)
- All 4 verification hooks return exit code 0 (`[PASS]`).
- 100% test pass rate with zero regressions.
- No unmasked PII in source files or logger statements.
- Published plans are provably immutable.
