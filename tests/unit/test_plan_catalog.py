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

def test_plan_attribute_validations():
    """Validates boundary constraints on plan attributes."""
    from src.domain.plan_policy import PlanPolicy
    
    # 1. Empty plan_id
    with pytest.raises(DomainException) as exc:
        PlanPolicy.validate_plan_attributes("", "Name", PlanType.PREPAID, Decimal("10.00"), 30, 10)
    assert exc.value.reason_code == "ERR_INVALID_PLAN_DATA"

    # 2. Empty name
    with pytest.raises(DomainException) as exc:
        PlanPolicy.validate_plan_attributes("PLAN-1", "   ", PlanType.PREPAID, Decimal("10.00"), 30, 10)
    assert exc.value.reason_code == "ERR_INVALID_PLAN_DATA"

    # 3. Validity <= 0
    with pytest.raises(DomainException) as exc:
        PlanPolicy.validate_plan_attributes("PLAN-1", "Plan 1", PlanType.PREPAID, Decimal("10.00"), 0, 10)
    assert exc.value.reason_code == "ERR_INVALID_PLAN_DATA"

    # 4. Data < 0
    with pytest.raises(DomainException) as exc:
        PlanPolicy.validate_plan_attributes("PLAN-1", "Plan 1", PlanType.PREPAID, Decimal("10.00"), 30, -5)
    assert exc.value.reason_code == "ERR_INVALID_PLAN_DATA"

    # 5. Postpaid rent <= 0
    with pytest.raises(DomainException) as exc:
        PlanPolicy.validate_plan_attributes("PLAN-1", "Plan 1", PlanType.POSTPAID, Decimal("0.00"), 30, 10)
    assert exc.value.reason_code == "ERR_INVALID_PLAN_DATA"

def test_publish_and_query_plans():
    srv = SubscriptionService()
    p = srv.create_plan("PLAN-PUB", "Draft Plan", PlanType.PREPAID, Decimal("15.00"), 28, 5, is_published=False)
    assert len(srv.list_plans(published_only=True)) == 0
    assert len(srv.list_plans(published_only=False)) == 1

    srv.publish_plan("PLAN-PUB")
    assert len(srv.list_plans(published_only=True)) == 1

    with pytest.raises(DomainException) as exc:
        srv.get_plan("PLAN-NON-EXISTENT")
    assert exc.value.reason_code == "ERR_PLAN_NOT_FOUND"

