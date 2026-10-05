from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

from src.domain.models import (
    PlanVersion, PlanType, PlanChangeTenureException, DomainException
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
        days_used: int = 0,
        cycle_days: int = 30,
        bypass_tenure: bool = False,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        # Validate tenure rule if not bypassed by CSR override
        if not bypass_tenure and current_plan.min_tenure_days > 0 and plan_activated_at:
            now = current_time or datetime.now(timezone.utc)
            served_tenure = (now - plan_activated_at).days
            if served_tenure < current_plan.min_tenure_days:
                raise PlanChangeTenureException(
                    f"Plan tenure requirement not met: required {current_plan.min_tenure_days} days, served {served_tenure} days",
                    "ERR_MINIMUM_TENURE_NOT_MET"
                )

        # Classify migration direction
        is_upgrade = new_plan.monthly_rent > current_plan.monthly_rent

        # Calculate charges
        if current_plan.plan_type == PlanType.POSTPAID:
            itemized = ProRataCalculator.calculate_itemized(
                old_rent=current_plan.monthly_rent,
                new_rent=new_plan.monthly_rent,
                days_used=days_used,
                cycle_days=cycle_days
            )
            charge = itemized["total_charge"]
            effective_mode = "IMMEDIATE_PRO_RATA"
        else:
            # Prepaid plans activate immediately upon migration
            charge = new_plan.monthly_rent
            itemized = {
                "days_used": Decimal(str(days_used)),
                "days_remaining": Decimal(str(cycle_days - days_used)),
                "cycle_days": Decimal(str(cycle_days)),
                "old_component": Decimal("0.00"),
                "new_component": charge,
                "total_charge": charge
            }
            effective_mode = "IMMEDIATE_PREPAID"

        return {
            "is_upgrade": is_upgrade,
            "effective_mode": effective_mode,
            "charge": charge,
            "itemized": itemized
        }
