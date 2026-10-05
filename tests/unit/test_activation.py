import pytest
from decimal import Decimal
from src.domain.models import (
    SubscriberState, PlanType, PlanVersion,
    ActivationFailedException, InvalidSubscriberStateException
)
from src.services.subscription_service import SubscriptionService

@pytest.fixture
def service():
    srv = SubscriptionService()
    srv.create_plan(
        plan_id="PLAN-PRE-BASE",
        name="Prepaid Starter",
        plan_type=PlanType.PREPAID,
        monthly_rent=Decimal("15.00"),
        validity_days=28,
        data_gb=10,
        is_published=True
    )
    srv.create_plan(
        plan_id="PLAN-POST-BASE",
        name="Postpaid Silver",
        plan_type=PlanType.POSTPAID,
        monthly_rent=Decimal("45.00"),
        validity_days=30,
        data_gb=25,
        is_published=True
    )
    return srv

def test_ac_01_self_registration_pending_kyc_and_pii_masking(service):
    """AC-01: Self-register creates subscriber in PENDING_KYC with masked PII representation."""
    sub = service.register_subscriber("9876543210", "AADHAAR-9999", PlanType.PREPAID)
    assert sub.state == SubscriberState.PENDING_KYC
    assert sub.subscriber_id.startswith("SUB-")
    
    masked = sub.mask_pii()
    assert masked["mobile_number"] == "XXXXXX3210"
    assert masked["identity_proof_ref"] == "[REDACTED]"
    assert masked["state"] == "PENDING_KYC"

def test_ac_08_successful_activation(service):
    """AC-08: All rules satisfied: transitions subscriber from PENDING_KYC to ACTIVE."""
    sub = service.register_subscriber("9123456789", "ID-PROOF-1", PlanType.POSTPAID)
    activated = service.activate_subscriber(
        subscriber_id=sub.subscriber_id,
        kyc_status="VERIFIED",
        dealer_code="DEALER_001",
        mnp_status="APPROVED",
        initial_plan_id="PLAN-POST-BASE"
    )
    assert activated.state == SubscriberState.ACTIVE
    assert activated.current_plan_id == "PLAN-POST-BASE"
    assert activated.mobile_number in service.subscriber_repo.get_active_numbers()
    assert activated.is_consumption_active is True

def test_ac_08_kyc_unverified_rejection(service):
    """AC-08: Unverified KYC fails activation with ERR_KYC_FAILED."""
    sub = service.register_subscriber("9123456780", "ID-PROOF-2", PlanType.PREPAID)
    with pytest.raises(ActivationFailedException) as exc_info:
        service.activate_subscriber(
            subscriber_id=sub.subscriber_id,
            kyc_status="UNVERIFIED",
            dealer_code="DEALER_001",
            mnp_status="APPROVED",
            initial_plan_id="PLAN-PRE-BASE"
        )
    assert exc_info.value.reason_code == "ERR_KYC_FAILED"
    assert sub.state == SubscriberState.PENDING_KYC

def test_ac_08_invalid_dealer_code_rejection(service):
    """AC-08: Invalid dealer code fails activation with ERR_INVALID_DEALER."""
    sub = service.register_subscriber("9123456781", "ID-PROOF-3", PlanType.PREPAID)
    with pytest.raises(ActivationFailedException) as exc_info:
        service.activate_subscriber(
            subscriber_id=sub.subscriber_id,
            kyc_status="VERIFIED",
            dealer_code="UNAUTHORIZED_VENDOR",
            mnp_status="APPROVED",
            initial_plan_id="PLAN-PRE-BASE"
        )
    assert exc_info.value.reason_code == "ERR_INVALID_DEALER"

def test_ac_08_mnp_rejected_rejection(service):
    """AC-08: Downstream MNP rejection fails activation with ERR_MNP_REJECTED."""
    sub = service.register_subscriber("9123456782", "ID-PROOF-4", PlanType.PREPAID)
    with pytest.raises(ActivationFailedException) as exc_info:
        service.activate_subscriber(
            subscriber_id=sub.subscriber_id,
            kyc_status="VERIFIED",
            dealer_code="DEALER_002",
            mnp_status="REJECTED",
            initial_plan_id="PLAN-PRE-BASE"
        )
    assert exc_info.value.reason_code == "ERR_MNP_REJECTED"

def test_ac_08_duplicate_active_mobile_number_forbidden(service):
    """AC-08 & NFR-08: Duplicate active subscriptions on identical mobile number are blocked."""
    sub1 = service.register_subscriber("9988776655", "ID-A", PlanType.POSTPAID)
    service.activate_subscriber(sub1.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-BASE")
    
    sub2 = service.register_subscriber("9988776655", "ID-B", PlanType.POSTPAID)
    with pytest.raises(ActivationFailedException) as exc_info:
        service.activate_subscriber(sub2.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-BASE")
    assert exc_info.value.reason_code == "ERR_DUPLICATE_ACTIVE_NUMBER"
