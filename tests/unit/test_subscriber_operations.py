import pytest
from decimal import Decimal
from datetime import datetime, timezone
from src.domain.models import SubscriberState, PlanType, PlanVersion, InvalidSubscriberStateException, PlanImmutableException, ActivationFailedException
from src.services.subscription_service import SubscriptionService

@pytest.fixture
def service():
    srv = SubscriptionService()
    srv.plans["PLAN-PRE-01"] = PlanVersion("PLAN-PRE-01", 1, "Prepaid Basic", PlanType.PREPAID, Decimal("10.00"), 28, 5, is_published=True)
    srv.plans["PLAN-POST-01"] = PlanVersion("PLAN-POST-01", 1, "Postpaid Silver", PlanType.POSTPAID, Decimal("50.00"), 30, 20, is_published=True)
    srv.plans["PLAN-POST-02"] = PlanVersion("PLAN-POST-02", 1, "Postpaid Gold", PlanType.POSTPAID, Decimal("100.00"), 30, 50, is_published=True)
    return srv

def test_ac_01_self_registration(service):
    """AC-01: Self-register creates subscription in PENDING_KYC state."""
    sub = service.register_subscriber("9876543210", "ID-REF-999", PlanType.PREPAID)
    assert sub.state == SubscriberState.PENDING_KYC
    assert sub.subscriber_id.startswith("SUB-")

def test_ac_02_invalid_state_transition(service):
    """AC-02: Invalid state transition directly from PENDING_KYC to PORT_OUT_REQUESTED raises InvalidSubscriberStateException."""
    sub = service.register_subscriber("9876543210", "ID-REF-999", PlanType.PREPAID)
    with pytest.raises(InvalidSubscriberStateException) as exc_info:
        service.initiate_port_out(sub.subscriber_id)
    assert exc_info.value.reason_code == "ERR_INVALID_STATE_TRANSITION"

def test_ac_03_plan_immutability():
    """AC-03: Published plan versions cannot be modified."""
    plan = PlanVersion("PLAN-PUB", 1, "Immutable Plan", PlanType.POSTPAID, Decimal("99.00"), 30, 100, is_published=True)
    with pytest.raises(PlanImmutableException) as exc_info:
        plan.validate_immutability()
    assert exc_info.value.reason_code == "ERR_PLAN_IMMUTABLE"

def test_ac_05_pro_rata_billing_calculation(service):
    """AC-05: Mid-cycle postpaid plan changes compute exact pro-rata charges with fixed-point math."""
    sub = service.register_subscriber("9876543210", "ID-REF-999", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-01")
    
    result = service.change_plan(sub.subscriber_id, "PLAN-POST-02", days_used=10, cycle_days=30)
    
    # Calculation: (10/30 * 50.00) + (20/30 * 100.00) = 16.6666... + 66.6666... = 83.33
    assert result["pro_rata_charge"] == Decimal("83.33")

def test_ac_07_port_out_cooling_period_cancellation(service):
    """AC-07: Port-out initiates cooling period and allows cancellation back to ACTIVE."""
    sub = service.register_subscriber("9876543210", "ID-REF-999", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-01")
    
    service.initiate_port_out(sub.subscriber_id)
    assert service.get_subscriber(sub.subscriber_id).state == SubscriberState.PORT_OUT_REQUESTED
    
    service.cancel_port_out(sub.subscriber_id)
    assert service.get_subscriber(sub.subscriber_id).state == SubscriberState.ACTIVE

def test_ac_08_activation_rule_failures(service):
    """AC-08: Unverified KYC raises specific ActivationFailedException."""
    sub = service.register_subscriber("9876543210", "ID-REF-999", PlanType.PREPAID)
    with pytest.raises(ActivationFailedException) as exc_info:
        service.activate_subscriber(sub.subscriber_id, "UNVERIFIED", "DEALER_001", "APPROVED", "PLAN-PRE-01")
    assert exc_info.value.reason_code == "ERR_KYC_FAILED"

def test_ac_09_csr_override(service):
    """AC-09: CSR override forces activation and records audit trail with actor and timestamp."""
    sub = service.register_subscriber("9876543210", "ID-REF-999", PlanType.PREPAID)
    updated_sub = service.csr_override_activation(sub.subscriber_id, "PLAN-PRE-01", "CSR_AGENT_77", "OVERRIDE_KYC_MANUAL")
    
    assert updated_sub.state == SubscriberState.ACTIVE
    assert len(service.audit_logs) == 1
    assert service.audit_logs[0].actor == "CSR_AGENT_77"
    assert service.audit_logs[0].reason_code == "OVERRIDE_KYC_MANUAL"
