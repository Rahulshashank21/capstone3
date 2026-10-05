#!/usr/bin/env bash
set -euo pipefail

# Prioritize Python 3.13 where packages are installed
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:$PATH"

echo "=========================================================="
echo " Starting TelcoLane Subscriber & Plan Management Platform"
echo " Business Case: BC-AINE-020"
echo "=========================================================="

# Check and execute verification hooks prior to launching
echo "Executing preliminary substrate integrity verification..."
bash .claude/hooks/architecture-layering-check.sh
bash .claude/hooks/pii-masking-check.sh
bash .claude/hooks/pro-rata-invariant-check.sh
bash .claude/hooks/plan-immutability-check.sh

echo "Launching TelcoLane FastAPI server on http://127.0.0.1:8000 ..."
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000
