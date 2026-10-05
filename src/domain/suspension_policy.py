from typing import Optional
from src.domain.models import (
    Subscriber, SubscriberState, ConsumptionHaltedException,
    InvalidSubscriberStateException
)
from src.domain.state_machine import StateMachineValidator

class SuspensionPolicy:
    """Enforces rules for suspension, consumption halting, and service reactivation."""

    VALID_SUSPENSION_REASONS = {"REQUESTED_BY_USER", "NON_PAYMENT", "FRAUD_ALERT", "ADMIN_INTERVENTION"}

    @classmethod
    def validate_suspension(cls, subscriber: Subscriber, reason: str) -> None:
        StateMachineValidator.validate_transition(subscriber.state, SubscriberState.SUSPENDED)
        if reason not in cls.VALID_SUSPENSION_REASONS:
            reason = "REQUESTED_BY_USER"

    @classmethod
    def apply_suspension(cls, subscriber: Subscriber) -> None:
        subscriber.state = SubscriberState.SUSPENDED
        subscriber.is_consumption_active = False

    @classmethod
    def validate_reactivation(cls, subscriber: Subscriber) -> None:
        StateMachineValidator.validate_transition(subscriber.state, SubscriberState.ACTIVE)

    @classmethod
    def apply_reactivation(cls, subscriber: Subscriber) -> None:
        subscriber.state = SubscriberState.ACTIVE
        subscriber.is_consumption_active = True

    @classmethod
    def assert_consumption_permitted(cls, subscriber: Subscriber) -> None:
        if subscriber.state != SubscriberState.ACTIVE or not subscriber.is_consumption_active:
            raise ConsumptionHaltedException(
                f"Network consumption halted: subscriber is in state {subscriber.state}",
                "ERR_CONSUMPTION_HALTED"
            )
