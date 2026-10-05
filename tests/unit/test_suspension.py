import pytest
from decimal import Decimal
from src.domain.models import (
    SubscriberState, PlanType, ConsumptionHaltedException,
    InvalidSubscriberStateException
)
from src.services.subscription_service import SubscriptionService

@pytest.fixture
def service():
    srv = SubscriptionService()
    srv.create_plan("PLAN-PRE-SUSP", "Suspension Test Plan", PlanType.PREPAID, Decimal("15.00"), 28, 5, is_published=True)
    return srv

def test_ac_06_suspension_moves_to_suspended_and_halts_consumption(service):
    """AC-06: Moving subscriber to SUSPENDED halts network consumption."""
    sub = service.register_subscriber("9876543220", "ID-SUSP-1", PlanType.PREPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PRE-SUSP")
    
    # Active subscriber can consume
    assert service.assert_can_consume(sub.subscriber_id) is True
    
    # Suspend subscriber
    suspended = service.suspend_subscriber(sub.subscriber_id, reason="REQUESTED_BY_USER")
    assert suspended.state == SubscriberState.SUSPENDED
    assert suspended.is_consumption_active is False
    
    # Consumption blocked
    with pytest.raises(ConsumptionHaltedException) as exc_info:
        service.assert_can_consume(sub.subscriber_id)
    assert exc_info.value.reason_code == "ERR_CONSUMPTION_HALTED"

def test_ac_06_reactivation_restores_active_state_and_resumes_consumption(service):
    """AC-06: Reactivating a suspended subscriber restores state to ACTIVE and resumes consumption."""
    sub = service.register_subscriber("9876543221", "ID-SUSP-2", PlanType.PREPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PRE-SUSP")
    
    service.suspend_subscriber(sub.subscriber_id, reason="NON_PAYMENT")
    assert service.get_subscriber(sub.subscriber_id).state == SubscriberState.SUSPENDED
    
    reactivated = service.reactivate_subscriber(sub.subscriber_id)
    assert reactivated.state == SubscriberState.ACTIVE
    assert reactivated.is_consumption_active is True
    assert service.assert_can_consume(sub.subscriber_id) is True

def test_ac_06_cannot_suspend_unregistered_or_terminated_subscriber(service):
    """AC-06: Invalid transitions to SUSPENDED raise InvalidSubscriberStateException."""
    sub = service.register_subscriber("9876543222", "ID-SUSP-3", PlanType.PREPAID)
    # Still in PENDING_KYC
    with pytest.raises(InvalidSubscriberStateException) as exc_info:
        service.suspend_subscriber(sub.subscriber_id)
    assert exc_info.value.reason_code == "ERR_INVALID_STATE_TRANSITION"
