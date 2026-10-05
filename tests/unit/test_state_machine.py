import pytest
from src.domain.models import SubscriberState, InvalidSubscriberStateException
from src.domain.state_machine import StateMachineValidator

def test_ac_02_legal_state_transitions():
    """AC-02: Verifies all valid subscriber transitions pass validation."""
    valid_transitions = [
        (SubscriberState.PENDING_KYC, SubscriberState.ACTIVE),
        (SubscriberState.PENDING_KYC, SubscriberState.TERMINATED),
        (SubscriberState.ACTIVE, SubscriberState.SUSPENDED),
        (SubscriberState.ACTIVE, SubscriberState.PORT_OUT_REQUESTED),
        (SubscriberState.ACTIVE, SubscriberState.TERMINATED),
        (SubscriberState.SUSPENDED, SubscriberState.ACTIVE),
        (SubscriberState.SUSPENDED, SubscriberState.TERMINATED),
        (SubscriberState.PORT_OUT_REQUESTED, SubscriberState.ACTIVE),
        (SubscriberState.PORT_OUT_REQUESTED, SubscriberState.PORTED_OUT),
        (SubscriberState.PORT_OUT_REQUESTED, SubscriberState.TERMINATED),
    ]
    for current, target in valid_transitions:
        StateMachineValidator.validate_transition(current, target)
        assert StateMachineValidator.is_transition_allowed(current, target) is True

def test_ac_02_illegal_state_transitions():
    """AC-02: Verifies invalid subscriber transitions raise InvalidSubscriberStateException."""
    invalid_transitions = [
        (SubscriberState.PENDING_KYC, SubscriberState.PORT_OUT_REQUESTED),
        (SubscriberState.PENDING_KYC, SubscriberState.SUSPENDED),
        (SubscriberState.PENDING_KYC, SubscriberState.PORTED_OUT),
        (SubscriberState.PORTED_OUT, SubscriberState.ACTIVE),
        (SubscriberState.PORTED_OUT, SubscriberState.PENDING_KYC),
        (SubscriberState.TERMINATED, SubscriberState.ACTIVE),
        (SubscriberState.TERMINATED, SubscriberState.SUSPENDED),
    ]
    for current, target in invalid_transitions:
        with pytest.raises(InvalidSubscriberStateException) as exc_info:
            StateMachineValidator.validate_transition(current, target)
        assert exc_info.value.reason_code == "ERR_INVALID_STATE_TRANSITION"
        assert StateMachineValidator.is_transition_allowed(current, target) is False
