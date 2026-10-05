from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from src.domain.models import (
    PlanVersion, PlanType, PlanImmutableException,
    PlanChangeTenureException, DomainException
)

class PlanPolicy:
    """Enforces plan creation constraints, immutability, and subscriber tenure eligibility."""

    @staticmethod
    def validate_plan_attributes(
        plan_id: str,
        name: str,
        plan_type: PlanType,
        monthly_rent: Decimal,
        validity_days: int,
        data_gb: int
    ) -> None:
        if not plan_id or not plan_id.strip():
            raise DomainException("Plan ID cannot be empty", "ERR_INVALID_PLAN_DATA")
        if not name or not name.strip():
            raise DomainException("Plan name cannot be empty", "ERR_INVALID_PLAN_DATA")
        if validity_days <= 0:
            raise DomainException("Validity days must be strictly greater than 0", "ERR_INVALID_PLAN_DATA")
        if data_gb < 0:
            raise DomainException("Data quota cannot be negative", "ERR_INVALID_PLAN_DATA")
        if plan_type == PlanType.POSTPAID and monthly_rent <= Decimal("0.00"):
            raise DomainException("Postpaid plan must have a monthly rent greater than 0.00", "ERR_INVALID_PLAN_DATA")

    @staticmethod
    def assert_immutable(plan: PlanVersion) -> None:
        if plan.is_published:
            raise PlanImmutableException(
                f"Plan version '{plan.plan_id}:v{plan.version}' is published and immutable",
                "ERR_PLAN_IMMUTABLE"
            )

    @staticmethod
    def validate_tenure_requirement(
        current_plan: PlanVersion,
        plan_activated_at: Optional[datetime],
        current_time: Optional[datetime] = None
    ) -> None:
        if current_plan.min_tenure_days <= 0 or plan_activated_at is None:
            return

        now = current_time or datetime.now(timezone.utc)
        tenure_days = (now - plan_activated_at).days

        if tenure_days < current_plan.min_tenure_days:
            raise PlanChangeTenureException(
                f"Minimum tenure of {current_plan.min_tenure_days} days not met (served: {tenure_days} days)",
                "ERR_MINIMUM_TENURE_NOT_MET"
            )
