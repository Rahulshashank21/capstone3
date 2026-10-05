#!/usr/bin/env bash
set -euo pipefail

echo "Running Plan Immutability Verification Hook..."
python3 -c "
from decimal import Decimal
from src.domain.models import PlanVersion, PlanType, PlanImmutableException

plan = PlanVersion(
    plan_id='PLAN-TEST-IMMUTABLE',
    version=1,
    name='Test Plan',
    plan_type=PlanType.POSTPAID,
    monthly_rent=Decimal('49.99'),
    validity_days=30,
    data_gb=20,
    is_published=True
)

try:
    plan.validate_immutability()
    print('[FAIL] Expected PlanImmutableException on published plan validation!')
    exit(1)
except PlanImmutableException as e:
    assert e.reason_code == 'ERR_PLAN_IMMUTABLE', f'Unexpected reason code: {e.reason_code}'
    print('[PASS] Plan immutability invariant verified successfully.')
"
