import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from src.domain.models import (
    SubscriberState, PlanType, PlanVersion,
    PlanChangeTenureException, InvalidSubscriberStateException
)
from src.services.subscription_service import SubscriptionService

@pytest.fixture
def service():
    srv = SubscriptionService()
    srv.create_plan(
        plan_id="PLAN-PRE-A",
        name="Prepaid Starter 28D",
        plan_type=PlanType.PREPAID,
        monthly_rent=Decimal("20.00"),
        validity_days=28,
        data_gb=10,
        is_published=True
    )
    srv.create_plan(
        plan_id="PLAN-PRE-B",
        name="Prepaid Pro 56D",
        plan_type=PlanType.PREPAID,
        monthly_rent=Decimal("45.00"),
        validity_days=56,
        data_gb=30,
        is_published=True
    )
    srv.create_plan(
        plan_id="PLAN-POST-TENURED",
        name="Postpaid Long Term",
        plan_type=PlanType.POSTPAID,
        monthly_rent=Decimal("60.00"),
        validity_days=30,
        data_gb=40,
        min_tenure_days=90,
        is_published=True
    )
    srv.create_plan(
        plan_id="PLAN-POST-UPGRADE",
        name="Postpaid Unlimited Max",
        plan_type=PlanType.POSTPAID,
        monthly_rent=Decimal("120.00"),
        validity_days=30,
        data_gb=150,
        min_tenure_days=0,
        is_published=True
    )
    return srv

def test_ac_04_prepaid_immediate_upgrade(service):
    """AC-04: Prepaid plan upgrade takes effect immediately."""
    sub = service.register_subscriber("9876543210", "ID-111", PlanType.PREPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PRE-A")
    
    result = service.change_plan(sub.subscriber_id, "PLAN-PRE-B")
    assert result["new_plan_id"] == "PLAN-PRE-B"
    assert result["old_plan_id"] == "PLAN-PRE-A"
    
    updated_sub = service.get_subscriber(sub.subscriber_id)
    assert updated_sub.current_plan_id == "PLAN-PRE-B"

def test_ac_04_minimum_tenure_enforcement_blocks_early_change(service):
    """AC-04: Minimum tenure requirement blocks premature plan changes."""
    sub = service.register_subscriber("9876543211", "ID-222", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-TENURED")
    
    # Subscribed only 5 days ago (required: 90 days)
    sub.plan_activated_at = datetime.now(timezone.utc) - timedelta(days=5)
    service.subscriber_repo.save(sub)

    with pytest.raises(PlanChangeTenureException) as exc_info:
        service.change_plan(sub.subscriber_id, "PLAN-POST-UPGRADE")
    assert exc_info.value.reason_code == "ERR_MINIMUM_TENURE_NOT_MET"

def test_ac_04_satisfied_tenure_allows_plan_change(service):
    """AC-04: Subscriptions satisfying minimum tenure can change plans freely."""
    sub = service.register_subscriber("9876543212", "ID-333", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-TENURED")
    
    # Subscribed 95 days ago (required: 90 days)
    sub.plan_activated_at = datetime.now(timezone.utc) - timedelta(days=95)
    service.subscriber_repo.save(sub)

    result = service.change_plan(sub.subscriber_id, "PLAN-POST-UPGRADE", days_used=15, cycle_days=30)
    assert result["new_plan_id"] == "PLAN-POST-UPGRADE"
    assert service.get_subscriber(sub.subscriber_id).current_plan_id == "PLAN-POST-UPGRADE"

def test_ac_04_cannot_change_plan_if_not_active(service):
    """AC-04: Non-active subscribers cannot initiate plan changes."""
    sub = service.register_subscriber("9876543213", "ID-444", PlanType.PREPAID)
    with pytest.raises(InvalidSubscriberStateException) as exc_info:
        service.change_plan(sub.subscriber_id, "PLAN-PRE-B")
    assert exc_info.value.reason_code == "ERR_NOT_ACTIVE"

def test_plan_change_draft_plan_rejected(service):
    """Cannot migrate to unpublished draft plan."""
    service.create_plan("PLAN-DRAFT", "Draft Plan", PlanType.PREPAID, Decimal("10.00"), 28, 5, is_published=False)
    sub = service.register_subscriber("9876543214", "ID-555", PlanType.PREPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PRE-A")

    from src.domain.models import DomainException
    with pytest.raises(DomainException) as exc:
        service.change_plan(sub.subscriber_id, "PLAN-DRAFT")
    assert exc.value.reason_code == "ERR_PLAN_NOT_PUBLISHED"

def test_plan_change_identical_plan_rejected(service):
    """Cannot migrate to the identical currently enrolled plan."""
    sub = service.register_subscriber("9876543215", "ID-666", PlanType.PREPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PRE-A")

    from src.domain.models import DomainException
    with pytest.raises(DomainException) as exc:
        service.change_plan(sub.subscriber_id, "PLAN-PRE-A")
    assert exc.value.reason_code == "ERR_IDENTICAL_PLAN_MIGRATION"

def test_plan_change_incompatible_family_rejected(service):
    """Cannot migrate cross-family (Prepaid to Postpaid) directly."""
    sub = service.register_subscriber("9876543216", "ID-777", PlanType.PREPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PRE-A")

    from src.domain.models import DomainException
    with pytest.raises(DomainException) as exc:
        service.change_plan(sub.subscriber_id, "PLAN-POST-UPGRADE")
    assert exc.value.reason_code == "ERR_INCOMPATIBLE_PLAN_FAMILY"

def test_csr_override_plan_change_bypasses_tenure(service):
    """CSR override successfully bypasses minimum tenure requirement."""
    sub = service.register_subscriber("9876543217", "ID-888", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-TENURED")

    res = service.csr_override_plan_change(
        subscriber_id=sub.subscriber_id,
        new_plan_id="PLAN-POST-UPGRADE",
        actor_id="CSR_HERO",
        reason_code="OVERRIDE_TENURE_EXCEPTION",
        days_used=10,
        cycle_days=30
    )
    assert res["new_plan_id"] == "PLAN-POST-UPGRADE"
    assert service.get_subscriber(sub.subscriber_id).current_plan_id == "PLAN-POST-UPGRADE"
