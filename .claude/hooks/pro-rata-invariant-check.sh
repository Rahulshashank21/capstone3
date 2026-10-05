#!/usr/bin/env bash
set -euo pipefail

echo "Running Pro-Rata Non-Negative Invariant Verification..."
python3 -c "
from decimal import Decimal
from src.domain.rules import ProRataCalculator

calc = ProRataCalculator()
res = calc.calculate(
    old_rent=Decimal('100.00'),
    new_rent=Decimal('200.00'),
    days_used=10,
    cycle_days=30
)
assert res >= Decimal('0.00'), 'Pro-rata invariant failed: charges must be non-negative'
print('[PASS] Pro-rata charge invariant verified successfully.')
"
