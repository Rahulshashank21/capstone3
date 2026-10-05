# Command: /check-architecture

## Description
Executes architectural layer boundary tests to verify that domain rules have zero dependency on frameworks or adapters, services only interact with repositories and domain, and controllers guard role boundaries.

## Command Workflow
```bash
pytest tests/architecture/
bash .claude/hooks/architecture-layering-check.sh
```
