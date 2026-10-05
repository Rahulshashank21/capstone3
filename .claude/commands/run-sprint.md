# Command: /run-sprint

## Description
Executes a multi-agent sprint cycle using the Claude Harness Engine:
1. `planner` parses target sprint spec and acceptance criteria.
2. `generator` produces clean domain, service, and repository code.
3. `test-engineer` writes red-green-refactor test cases tagged with AC-NN IDs.
4. `evaluator` executes verification hooks and unit tests.
5. If clean, opens a PR branch and merges with `--no-ff`.

## Syntax
`/run-sprint [sprint-number]`
Example: `/run-sprint 1`
