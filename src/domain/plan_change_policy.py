from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

from src.domain.models import (
    PlanVersion, PlanType, PlanChangeTenureException, DomainException,
    ProRataCalculationException
)
from src.domain.pro_rata_calculator import ProRataCalculator

class PlanChangePolicy:
    """Business policy governing plan migrations, upgrades, downgrades, and tenure validation."""

    @classmethod
    def evaluate_migration(
        cls,
        current_plan: PlanVersion,
        new_plan: PlanVersion,
        plan_activated_at: Optional[datetime],
        initial_activated_at: Optional[datetime] = None,
        days_used: Optional[int] = None,
        cycle_days: int = 30,
        immediate_pro_rata: bool = False,
        bypass_tenure: bool = False,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        now = current_time or datetime.now(timezone.utc)

        # 1. Target plan published check
        if not new_plan.is_published:
            raise DomainException(
                f"Cannot migrate to draft or unpublished plan '{new_plan.plan_id}'",
                "ERR_PLAN_NOT_PUBLISHED",
                http_status=422
            )

        # 2. No-op identical plan check
        if new_plan.plan_id == current_plan.plan_id:
            raise DomainException(
                f"Subscriber is already enrolled on plan '{new_plan.plan_id}'",
                "ERR_IDENTICAL_PLAN_MIGRATION",
                http_status=409
            )

        # 3. Plan family compatibility
        if new_plan.plan_type != current_plan.plan_type:
            raise DomainException(
                f"Cross-family migration between {current_plan.plan_type.value} and {new_plan.plan_type.value} requires customer service conversion",
                "ERR_INCOMPATIBLE_PLAN_FAMILY",
                http_status=422
            )

        # 4. Tenure requirement validation (track from initial activation date to avoid reset traps)
        tenure_anchor = initial_activated_at or plan_activated_at
        if not bypass_tenure and current_plan.min_tenure_days > 0 and tenure_anchor:
            served_seconds = (now - tenure_anchor).total_seconds()
            served_days = int(served_seconds // 86400)
            if served_days < current_plan.min_tenure_days:
                raise PlanChangeTenureException(
                    f"Plan tenure requirement not met: required {current_plan.min_tenure_days} days, served {served_days} days",
                    "ERR_MINIMUM_TENURE_NOT_MET"
                )

        is_upgrade = new_plan.monthly_rent > current_plan.monthly_rent

        # 5. Postpaid vs Prepaid Execution Semantics (AC-04)
        if current_plan.plan_type == PlanType.POSTPAID:
            if not immediate_pro_rata:
                # AC-04 Standard Postpaid: Takes effect from next billing cycle boundary
                # Compute cycle anchor
                ref_time = plan_activated_at or now
                elapsed_days = int((now - ref_time).total_seconds() // 86400)
                current_cycle_pos = elapsed_days % cycle_days
                days_until_next_cycle = cycle_days - current_cycle_pos
                effective_from = now + timedelta(days=days_until_next_cycle)

                return {
                    "is_upgrade": is_upgrade,
                    "effective_mode": "SCHEDULED_NEXT_CYCLE",
                    "effective_from": effective_from,
                    "immediate_apply": False,
                    "charge": Decimal("0.00"),
                    "itemized": None
                }
            else:
                # Immediate mid-cycle migration with pro-rata charge calculation
                # Derive server-side days_used if not explicitly supplied
                if days_used is None:
                    ref_time = plan_activated_at or now
                    derived_used = int((now - ref_time).total_seconds() // 86400) % cycle_days
                    actual_days_used = min(max(derived_used, 0), cycle_days)
                else:
                    actual_days_used = days_used

                itemized = ProRataCalculator.calculate_itemized(
                    old_rent=current_plan.monthly_rent,
                    new_rent=new_plan.monthly_rent,
                    days_used=actual_days_used,
                    cycle_days=cycle_days
                )
                return {
                    "is_upgrade": is_upgrade,
                    "effective_mode": "IMMEDIATE_PRO_RATA",
                    "effective_from": now,
                    "immediate_apply": True,
                    "charge": itemized["total_charge"],
                    "itemized": itemized
                }
        else:
            # Prepaid: AC-04 Immediate upgrade upon payment
            return {
                "is_upgrade": is_upgrade,
                "effective_mode": "IMMEDIATE_PREPAID",
                "effective_from": now,
                "immediate_apply": True,
                "charge": new_plan.monthly_rent,
                "itemized": {
                    "days_used": Decimal("0"),
                    "days_remaining": Decimal(str(new_plan.validity_days)),
                    "cycle_days": Decimal(str(new_plan.validity_days)),
                    "old_component": Decimal("0.00"),
                    "new_component": new_plan.monthly_rent,
                    "total_charge": new_plan.monthly_rent
                }
            }
