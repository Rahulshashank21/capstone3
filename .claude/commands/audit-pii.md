# Command: /audit-pii

## Description
Scans the source code, loggers, and test suites for unmasked subscriber PII patterns (Aadhaar, PAN, raw 10-digit mobile numbers).

## Command Workflow
1. Run PII masking audit hook:
   ```bash
   bash .claude/hooks/pii-masking-check.sh
   ```
2. Scan source files for plain logging statements containing subscriber mobile numbers or identity proof refs:
   ```bash
   grep -rn "logger\." src/ | grep -v "mask_pii" || true
   ```
3. Report clean status or flag offending lines for immediate remediation.
