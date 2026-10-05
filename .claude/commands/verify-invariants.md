# Command: /verify-invariants

## Description
Executes the comprehensive invariant test suite across financial calculations, state machines, and plan immutability.

## Command Workflow
1. Execute pro-rata invariant check:
   ```bash
   bash .claude/hooks/pro-rata-invariant-check.sh
   ```
2. Execute plan immutability verification:
   ```bash
   bash .claude/hooks/plan-immutability-check.sh
   ```
3. Run Pytest unit and boundary tests:
   ```bash
   pytest tests/unit/test_subscriber_operations.py tests/unit/test_pro_rata_boundary.py
   ```
4. Report pass/fail summary.
