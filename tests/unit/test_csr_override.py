import pytest
from decimal import Decimal
from src.domain.models import (
    SubscriberState, PlanType, Role, UnauthorizedException, DomainException, ActivationFailedException
)
from src.domain.csr_override_policy import CSROverridePolicy
from src.services.subscription_service import SubscriptionService

@pytest.fixture
def service():
    srv = SubscriptionService()
    srv.create_plan("PLAN-PRE-OVR", "Prepaid Override Pack", PlanType.PREPAID, Decimal("10.00"), 28, 5, is_published=True)
    srv.create_plan("PLAN-POST-OVR", "Postpaid Override Pack", PlanType.POSTPAID, Decimal("50.00"), 30, 20, min_tenure_days=90, is_published=True)
    srv.create_plan("PLAN-POST-NEW", "Postpaid Target Plan", PlanType.POSTPAID, Decimal("80.00"), 30, 40, is_published=True)
    return srv

def test_ac_09_csr_activation_override(service):
    """AC-09: CSR successfully overrides activation failure and records audit log."""
    sub = service.register_subscriber("9876543240", "ID-REJECTED-KYC", PlanType.PREPAID)
    
    # Activation fails due to unverified KYC, creating rejection record
    with pytest.raises(ActivationFailedException) as exc:
        service.activate_subscriber(sub.subscriber_id, "REJECTED", "DEALER_001", "APPROVED", "PLAN-PRE-OVR")
    rejection_id = exc.value.rejection_id

    # CSR overrides KYC block with valid reason code
    activated = service.csr_override_activation(
        subscriber_id=sub.subscriber_id,
        initial_plan_id="PLAN-PRE-OVR",
        actor_id="CSR_AGENT_42",
        reason_code="OVERRIDE_KYC_MANUAL",
        rejection_id=rejection_id
    )
    assert activated.state == SubscriberState.ACTIVE
    assert activated.current_plan_id == "PLAN-PRE-OVR"
    
    # Audit log validation
    logs = service.audit_repo.find_by_actor("CSR_AGENT_42")
    assert len(logs) == 1
    assert logs[0].role == Role.CSR
    assert logs[0].reason_code == "OVERRIDE_KYC_MANUAL"
    assert logs[0].action == "CSR_ACTIVATION_OVERRIDE"

def test_csr_override_without_rejection_record_rejected(service):
    """Unconditional CSR override without prior rejection is blocked."""
    sub = service.register_subscriber("9876543249", "ID-NO-REJ", PlanType.PREPAID)
    with pytest.raises(DomainException) as exc:
        service.csr_override_activation(
            subscriber_id=sub.subscriber_id,
            initial_plan_id="PLAN-PRE-OVR",
            actor_id="CSR_AGENT_42",
            reason_code="OVERRIDE_KYC_MANUAL"
        )
    assert exc.value.reason_code == "ERR_REJECTION_REQUIRED"

def test_ac_09_csr_tenure_override_for_plan_change(service):
    """AC-09: CSR overrides minimum tenure requirement with OVERRIDE_TENURE_WAIVER."""
    sub = service.register_subscriber("9876543241", "ID-TENURE-1", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-OVR")

    # Subscriber has 0 days tenure, but CSR grants override waiver
    res = service.csr_override_plan_change(
        subscriber_id=sub.subscriber_id,
        new_plan_id="PLAN-POST-NEW",
        actor_id="CSR_SUPERVISOR_01",
        reason_code="OVERRIDE_TENURE_WAIVER",
        days_used=10,
        cycle_days=30
    )
    assert res["new_plan_id"] == "PLAN-POST-NEW"
    assert service.get_subscriber(sub.subscriber_id).current_plan_id == "PLAN-POST-NEW"

    logs = service.audit_repo.find_by_actor("CSR_SUPERVISOR_01")
    assert len(logs) == 1
    assert logs[0].reason_code == "OVERRIDE_TENURE_WAIVER"

def test_ac_09_unauthorized_role_rejected():
    """AC-09 & NFR-04: Non-CSR/ADMIN roles attempting overrides are rejected with ERR_UNAUTHORIZED."""
    with pytest.raises(UnauthorizedException) as exc_info:
        CSROverridePolicy.validate_override_request(Role.SUBSCRIBER, "OVERRIDE_KYC_MANUAL")
    assert exc_info.value.reason_code == "ERR_UNAUTHORIZED"

    with pytest.raises(UnauthorizedException) as exc_dealer:
        CSROverridePolicy.validate_override_request(Role.DEALER, "OVERRIDE_KYC_MANUAL")
    assert exc_dealer.value.reason_code == "ERR_UNAUTHORIZED"

def test_ac_09_invalid_reason_code_rejected():
    """AC-09: Unrecognized reason code is rejected with ERR_INVALID_REASON_CODE."""
    with pytest.raises(DomainException) as exc_info:
        CSROverridePolicy.validate_override_request(Role.CSR, "RANDOM_UNAUTHORIZED_JUSTIFICATION")
    assert exc_info.value.reason_code == "ERR_INVALID_REASON_CODE"
