import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from src.domain.models import (
    SubscriberState, PlanType, InvalidSubscriberStateException
)
from src.services.subscription_service import SubscriptionService

@pytest.fixture
def service():
    srv = SubscriptionService()
    srv.create_plan("PLAN-PORT-01", "Porting Plan", PlanType.POSTPAID, Decimal("40.00"), 30, 20, is_published=True)
    return srv

def test_ac_07_port_out_initiation_and_cooling_period(service):
    """AC-07: Initiating port-out moves state to PORT_OUT_REQUESTED and begins 7-day cooling window."""
    sub = service.register_subscriber("9876543230", "ID-PORT-1", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PORT-01")
    
    ported_sub = service.initiate_port_out(sub.subscriber_id, recipient_operator="REC_TELCO_5G")
    assert ported_sub.state == SubscriberState.PORT_OUT_REQUESTED
    assert ported_sub.port_out_requested_at is not None

def test_ac_07_port_out_cancellation_within_7_days(service):
    """AC-07: Cancellation within the 7-day window restores subscriber to ACTIVE state."""
    sub = service.register_subscriber("9876543231", "ID-PORT-2", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PORT-01")
    service.initiate_port_out(sub.subscriber_id)
    
    # 3 days elapsed (well within 7 days)
    sub.port_out_requested_at = datetime.now(timezone.utc) - timedelta(days=3)
    service.subscriber_repo.save(sub)

    cancelled_sub = service.cancel_port_out(sub.subscriber_id)
    assert cancelled_sub.state == SubscriberState.ACTIVE
    assert cancelled_sub.port_out_requested_at is None

def test_ac_07_port_out_cancellation_rejected_after_7_days(service):
    """AC-07: Cancellation attempted after 7 days is rejected with ERR_COOLING_PERIOD_EXPIRED."""
    sub = service.register_subscriber("9876543232", "ID-PORT-3", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PORT-01")
    service.initiate_port_out(sub.subscriber_id)
    
    # 8 days elapsed (> 7 days)
    sub.port_out_requested_at = datetime.now(timezone.utc) - timedelta(days=8)
    service.subscriber_repo.save(sub)

    with pytest.raises(InvalidSubscriberStateException) as exc_info:
        service.cancel_port_out(sub.subscriber_id)
    assert exc_info.value.reason_code == "ERR_COOLING_PERIOD_EXPIRED"

def test_ac_07_port_out_finalization_transitions_to_ported_out(service):
    """AC-07: Finalizing port-out transitions subscriber to terminal PORTED_OUT state and releases number."""
    sub = service.register_subscriber("9876543233", "ID-PORT-4", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PORT-01")
    service.initiate_port_out(sub.subscriber_id)
    sub.port_out_requested_at = datetime.now(timezone.utc) - timedelta(days=8)
    service.subscriber_repo.save(sub)
    
    finalized = service.finalize_port_out(sub.subscriber_id)
    assert finalized.state == SubscriberState.PORTED_OUT
    assert finalized.is_consumption_active is False
    assert sub.mobile_number not in service.subscriber_repo.get_active_numbers()

def test_port_out_invalid_recipient_operator(service):
    """Enforces allowlisted recipient operators."""
    from src.domain.models import DomainException
    sub = service.register_subscriber("9876543234", "ID-PORT-5", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PORT-01")

    with pytest.raises(DomainException) as exc:
        service.initiate_port_out(sub.subscriber_id, recipient_operator="MALICIOUS_OPERATOR")
    assert exc.value.reason_code == "ERR_INVALID_RECIPIENT_OPERATOR"

def test_port_out_admin_override_policy(service):
    """Admin override requires authorized role and mandatory reason code."""
    from src.domain.models import Role, UnauthorizedException, DomainException

    sub = service.register_subscriber("9876543235", "ID-PORT-6", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PORT-01")
    service.initiate_port_out(sub.subscriber_id, recipient_operator="JIO_IND")

    # Day 1: Finalization without override fails
    with pytest.raises(DomainException) as exc:
        service.finalize_port_out(sub.subscriber_id, force_override=False)
    assert exc.value.reason_code == "ERR_COOLING_PERIOD_NOT_ELAPSED"

    # Non-admin attempting override fails
    with pytest.raises(UnauthorizedException) as exc:
        service.finalize_port_out(sub.subscriber_id, force_override=True, caller_role=Role.CSR, override_reason="URGENT")
    assert exc.value.reason_code == "ERR_UNAUTHORIZED_COOLING_OVERRIDE"

    # Admin without reason code fails
    with pytest.raises(DomainException) as exc:
        service.finalize_port_out(sub.subscriber_id, force_override=True, caller_role=Role.ADMIN, override_reason="")
    assert exc.value.reason_code == "ERR_OVERRIDE_REASON_REQUIRED"

    # Admin with valid reason succeeds
    finalized = service.finalize_port_out(
        sub.subscriber_id,
        force_override=True,
        caller_role=Role.ADMIN,
        override_reason="COURT_COMPLIANCE_EXPEDITE"
    )
    assert finalized.state == SubscriberState.PORTED_OUT

