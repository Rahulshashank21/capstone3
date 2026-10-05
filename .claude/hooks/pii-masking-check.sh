#!/usr/bin/env bash
set -euo pipefail

echo "Running PII Masking Audit..."
FOUND_PII=$(grep -rE "(aadhaar|pan|mobile_number)\s*=\s*\"[0-9]{10,12}\"" src/ || true)

if [ -n "$FOUND_PII" ]; then
    echo "[ERROR] Unmasked PII patterns detected in source files:"
    echo "$FOUND_PII"
    exit 1
fi

echo "[PASS] PII Masking verification succeeded."
exit 0
