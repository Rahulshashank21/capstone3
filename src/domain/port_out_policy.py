from datetime import datetime, timezone, timedelta
from typing import Optional
from src.domain.models import (
    Subscriber, SubscriberState, InvalidSubscriberStateException,
    CoolingPeriodExpiredException
)
from src.domain.state_machine import StateMachineValidator

class PortOutPolicy:
    """Manages the regulatory 7-day port-out cooling period and lifecycle transitions."""

    COOLING_PERIOD_DAYS = 7

    @classmethod
    def validate_initiation(cls, subscriber: Subscriber) -> None:
        StateMachineValidator.validate_transition(subscriber.state, SubscriberState.PORT_OUT_REQUESTED)

    @classmethod
    def apply_initiation(cls, subscriber: Subscriber, timestamp: Optional[datetime] = None) -> None:
        now = timestamp or datetime.now(timezone.utc)
        subscriber.state = SubscriberState.PORT_OUT_REQUESTED
        subscriber.port_out_requested_at = now

    @classmethod
    def validate_cancellation(cls, subscriber: Subscriber, current_time: Optional[datetime] = None) -> None:
        if subscriber.state != SubscriberState.PORT_OUT_REQUESTED:
            raise InvalidSubscriberStateException(
                f"Cannot cancel port-out for subscriber in state {subscriber.state}",
                "ERR_INVALID_STATE"
            )

        if subscriber.port_out_requested_at:
            now = current_time or datetime.now(timezone.utc)
            elapsed = now - subscriber.port_out_requested_at
            if elapsed > timedelta(days=cls.COOLING_PERIOD_DAYS):
                raise CoolingPeriodExpiredException(
                    f"Port-out cooling period of {cls.COOLING_PERIOD_DAYS} days has expired (elapsed: {elapsed.days} days)",
                    "ERR_COOLING_PERIOD_EXPIRED"
                )

        StateMachineValidator.validate_transition(subscriber.state, SubscriberState.ACTIVE)

    @classmethod
    def apply_cancellation(cls, subscriber: Subscriber) -> None:
        subscriber.state = SubscriberState.ACTIVE
        subscriber.port_out_requested_at = None

    @classmethod
    def validate_finalization(cls, subscriber: Subscriber, current_time: Optional[datetime] = None) -> None:
        if subscriber.state != SubscriberState.PORT_OUT_REQUESTED:
            raise InvalidSubscriberStateException(
                f"Cannot finalize port-out for subscriber in state {subscriber.state}",
                "ERR_INVALID_STATE"
            )
        StateMachineValidator.validate_transition(subscriber.state, SubscriberState.PORTED_OUT)

    @classmethod
    def apply_finalization(cls, subscriber: Subscriber) -> None:
        subscriber.state = SubscriberState.PORTED_OUT
        subscriber.is_consumption_active = False
