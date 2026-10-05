from typing import Optional
from src.domain.models import (
    Subscriber, SubscriberState, ConsumptionHaltedException,
    InvalidSubscriberStateException
)
from src.domain.state_machine import StateMachineValidator

class SuspensionPolicy:
    """Enforces rules for suspension, consumption halting, and prior state restoration."""

    VALID_SUSPENSION_REASONS = {"REQUESTED_BY_USER", "NON_PAYMENT", "FRAUD_ALERT", "ADMIN_INTERVENTION"}

    @classmethod
    def validate_suspension(cls, subscriber: Subscriber, reason: str) -> None:
        StateMachineValidator.validate_transition(subscriber.state, SubscriberState.SUSPENDED)
        if reason not in cls.VALID_SUSPENSION_REASONS:
            reason = "REQUESTED_BY_USER"

    @classmethod
    def apply_suspension(cls, subscriber: Subscriber, reason: str = "REQUESTED_BY_USER") -> None:
        subscriber.previous_state = subscriber.state
        subscriber.suspension_reason = reason
        subscriber.state = SubscriberState.SUSPENDED
        subscriber.is_consumption_active = False

    @classmethod
    def validate_reactivation(cls, subscriber: Subscriber) -> None:
        # Strict state guard: Only SUSPENDED subscribers can be reactivated
        if subscriber.state != SubscriberState.SUSPENDED:
            raise InvalidSubscriberStateException(
                f"Cannot reactivate subscriber in state '{subscriber.state.value}'. Only SUSPENDED subscribers can be reactivated.",
                "ERR_NOT_SUSPENDED"
            )
        target_state = subscriber.previous_state or SubscriberState.ACTIVE
        StateMachineValidator.validate_transition(subscriber.state, target_state)

    @classmethod
    def apply_reactivation(cls, subscriber: Subscriber) -> None:
        target_state = subscriber.previous_state or SubscriberState.ACTIVE
        subscriber.state = target_state
        subscriber.previous_state = None
        subscriber.suspension_reason = None
        subscriber.is_consumption_active = True

    @classmethod
    def assert_consumption_permitted(cls, subscriber: Subscriber) -> None:
        if subscriber.state != SubscriberState.ACTIVE or not subscriber.is_consumption_active:
            raise ConsumptionHaltedException(
                f"Network consumption halted: subscriber is in state '{subscriber.state.value}' (consumption active: {subscriber.is_consumption_active})",
                "ERR_CONSUMPTION_HALTED"
            )
