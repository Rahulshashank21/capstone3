# Testing Directives (tests/CLAUDE.md)

## Purpose & Scope
Governs automated testing standards for the TelcoLane platform.

## Core Rules
1. **Acceptance Criteria Tagging**: Every test verifying functional requirements must tag the specific AC ID in its docstring and test name (e.g. `test_ac_01_self_registration`, `test_ac_05_pro_rata_boundary`).
2. **Coverage Thresholds**: Target minimum 90% branch and line coverage across domain and services. Generate and commit `coverage.xml`.
3. **Architecture Tests**: Maintain at least 3 structural architecture tests in `tests/architecture/` enforcing layer isolation, immutability, and zero domain leakage.
4. **Boundary Testing**: Pro-rata billing tests must include cycle days 0, 1, cycle_days - 1, and cycle_days, as well as leap year months (29 days) and standard calendar lengths (28, 30, 31).
5. **Red-Green-Refactor Trail**: Document test-driven development cycles in `docs/tdd.md`.
