import pytest
from decimal import Decimal
from src.domain.models import PlanVersion, PlanType, PlanImmutableException, DomainException
from src.services.subscription_service import SubscriptionService

def test_ac_03_prepaid_and_postpaid_catalog_support():
    """AC-03: Catalog supports both prepaid validity-based and postpaid cycle-based plans."""
    srv = SubscriptionService()
    prepaid = srv.create_plan(
        plan_id="PLAN-PRE-100",
        name="Prepaid Value Pack",
        plan_type=PlanType.PREPAID,
        monthly_rent=Decimal("19.99"),
        validity_days=84,
        data_gb=50,
        voice_minutes=-1,
        sms_count=100,
        is_published=False
    )
    assert prepaid.plan_type == PlanType.PREPAID
    assert prepaid.validity_days == 84
    assert prepaid.version == 1

    postpaid = srv.create_plan(
        plan_id="PLAN-POST-500",
        name="Postpaid Enterprise 5G",
        plan_type=PlanType.POSTPAID,
        monthly_rent=Decimal("79.99"),
        validity_days=30,
        data_gb=100,
        voice_minutes=-1,
        sms_count=-1,
        is_published=False
    )
    assert postpaid.plan_type == PlanType.POSTPAID
    assert postpaid.monthly_rent == Decimal("79.99")
    assert postpaid.version == 1

def test_ac_03_plan_immutability_enforced():
    """AC-03 & NFR-02: Published plan versions cannot be altered in place."""
    srv = SubscriptionService()
    srv.create_plan(
        plan_id="PLAN-IMMUTABLE-01",
        name="Published Fixed Plan",
        plan_type=PlanType.POSTPAID,
        monthly_rent=Decimal("59.99"),
        validity_days=30,
        data_gb=30,
        is_published=True
    )
    
    # Overwriting published version directly in repository raises exception
    with pytest.raises(PlanImmutableException) as exc_info:
        srv.plan_repo.save(PlanVersion(
            plan_id="PLAN-IMMUTABLE-01",
            version=1,
            name="Attempted Altered Name",
            plan_type=PlanType.POSTPAID,
            monthly_rent=Decimal("19.99"),
            validity_days=30,
            data_gb=30,
            is_published=True
        ))
    assert exc_info.value.reason_code == "ERR_PLAN_IMMUTABLE"

def test_ac_03_plan_version_incrementing():
    """AC-03: Updating a plan creates sequential immutable versions."""
    srv = SubscriptionService()
    v1 = srv.create_plan("PLAN-EVOLVE", "Initial Tariff", PlanType.POSTPAID, Decimal("30.00"), 30, 10, is_published=True)
    assert v1.version == 1
    
    v2 = srv.create_plan("PLAN-EVOLVE", "Tariff Rev 2", PlanType.POSTPAID, Decimal("35.00"), 30, 15, is_published=True)
    assert v2.version == 2
    
    # Both versions are independently retrievable
    retrieved_v1 = srv.get_plan("PLAN-EVOLVE", version=1)
    retrieved_v2 = srv.get_plan("PLAN-EVOLVE", version=2)
    assert retrieved_v1.monthly_rent == Decimal("30.00")
    assert retrieved_v2.monthly_rent == Decimal("35.00")
