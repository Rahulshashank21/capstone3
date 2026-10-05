from typing import Dict, List
from src.domain.models import SubscriberState, InvalidSubscriberStateException

class StateMachineValidator:
    """Enforces legal telecom subscriber lifecycle transitions and prevents no-op or out-of-order jumps."""

    VALID_TRANSITIONS: Dict[SubscriberState, List[SubscriberState]] = {
        SubscriberState.PENDING_KYC: [
            SubscriberState.ACTIVE,
            SubscriberState.TERMINATED
        ],
        SubscriberState.ACTIVE: [
            SubscriberState.SUSPENDED,
            SubscriberState.PORT_OUT_REQUESTED,
            SubscriberState.TERMINATED
        ],
        SubscriberState.SUSPENDED: [
            SubscriberState.ACTIVE,
            SubscriberState.TERMINATED
        ],
        SubscriberState.PORT_OUT_REQUESTED: [
            SubscriberState.ACTIVE,
            SubscriberState.PORTED_OUT,
            SubscriberState.TERMINATED
        ],
        SubscriberState.PORTED_OUT: [],
        SubscriberState.TERMINATED: []
    }

    @classmethod
    def validate_transition(cls, current: SubscriberState, target: SubscriberState) -> None:
        if current == target:
            raise InvalidSubscriberStateException(
                f"Redundant state transition: subscriber is already in state '{current.value}'",
                "ERR_SAME_STATE_TRANSITION"
            )
        allowed = cls.VALID_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise InvalidSubscriberStateException(
                f"Invalid lifecycle transition from '{current.value}' to '{target.value}'",
                "ERR_INVALID_STATE_TRANSITION"
            )

    @classmethod
    def is_transition_allowed(cls, current: SubscriberState, target: SubscriberState) -> bool:
        if current == target:
            return False
        return target in cls.VALID_TRANSITIONS.get(current, [])
