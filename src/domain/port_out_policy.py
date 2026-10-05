from datetime import datetime, timezone, timedelta
from typing import Optional
from src.domain.models import (
    Subscriber, SubscriberState, InvalidSubscriberStateException,
    CoolingPeriodExpiredException, DomainException, RecipientOperator, Role
)
from src.domain.state_machine import StateMachineValidator

class PortOutPolicy:
    """Manages regulatory 7-day port-out cooling period, operator validation, cancellation, and finalization."""

    COOLING_PERIOD_DAYS = 7

    @classmethod
    def validate_operator(cls, recipient_operator: str) -> RecipientOperator:
        clean_op = (recipient_operator or "").strip().upper()
        try:
            return RecipientOperator(clean_op)
        except ValueError:
            valid_list = [op.value for op in RecipientOperator]
            raise DomainException(
                f"Invalid or unauthorized recipient operator: '{recipient_operator}'. Allowed: {valid_list}",
                "ERR_INVALID_RECIPIENT_OPERATOR",
                http_status=422
            )

    @classmethod
    def validate_initiation(cls, subscriber: Subscriber, recipient_operator: str) -> RecipientOperator:
        StateMachineValidator.validate_transition(subscriber.state, SubscriberState.PORT_OUT_REQUESTED)
        return cls.validate_operator(recipient_operator)

    @classmethod
    def apply_initiation(cls, subscriber: Subscriber, timestamp: Optional[datetime] = None) -> None:
        now = timestamp or datetime.now(timezone.utc)
        subscriber.state = SubscriberState.PORT_OUT_REQUESTED
        subscriber.port_out_requested_at = now

    @classmethod
    def validate_cancellation(cls, subscriber: Subscriber, current_time: Optional[datetime] = None) -> None:
        if subscriber.state != SubscriberState.PORT_OUT_REQUESTED:
            raise InvalidSubscriberStateException(
                f"Cannot cancel port-out: subscriber is in state '{subscriber.state.value}'. Must be PORT_OUT_REQUESTED.",
                "ERR_INVALID_STATE"
            )

        if subscriber.port_out_requested_at:
            now = current_time or datetime.now(timezone.utc)
            elapsed = now - subscriber.port_out_requested_at
            if elapsed > timedelta(days=cls.COOLING_PERIOD_DAYS):
                raise CoolingPeriodExpiredException(
                    f"Port-out cooling period of {cls.COOLING_PERIOD_DAYS} days has expired (elapsed: {elapsed.days} days). Request cannot be cancelled.",
                    "ERR_COOLING_PERIOD_EXPIRED"
                )

        StateMachineValidator.validate_transition(subscriber.state, SubscriberState.ACTIVE)

    @classmethod
    def apply_cancellation(cls, subscriber: Subscriber) -> None:
        subscriber.state = SubscriberState.ACTIVE
        subscriber.port_out_requested_at = None

    @classmethod
    def validate_finalization(
        cls,
        subscriber: Subscriber,
        current_time: Optional[datetime] = None,
        force_override: bool = False,
        caller_role: Optional[Role] = None,
        override_reason: Optional[str] = None
    ) -> None:
        if subscriber.state != SubscriberState.PORT_OUT_REQUESTED:
            raise InvalidSubscriberStateException(
                f"Cannot finalize port-out: subscriber is in state '{subscriber.state.value}'. Must be PORT_OUT_REQUESTED.",
                "ERR_INVALID_STATE"
            )

        if force_override:
            if caller_role and caller_role != Role.ADMIN:
                from src.domain.models import UnauthorizedException
                raise UnauthorizedException(
                    "Only ADMIN role may force override the 7-day port-out cooling period",
                    "ERR_UNAUTHORIZED_COOLING_OVERRIDE"
                )
            if not override_reason or not override_reason.strip():
                raise DomainException(
                    "A mandatory override reason code is required to bypass the cooling period",
                    "ERR_OVERRIDE_REASON_REQUIRED",
                    http_status=422
                )
        elif subscriber.port_out_requested_at:
            now = current_time or datetime.now(timezone.utc)
            elapsed = now - subscriber.port_out_requested_at
            if elapsed < timedelta(days=cls.COOLING_PERIOD_DAYS):
                remaining_hours = int((timedelta(days=cls.COOLING_PERIOD_DAYS) - elapsed).total_seconds() // 3600)
                raise DomainException(
                    f"Port-out cooling period has not elapsed yet ({remaining_hours} hours remaining). Cannot finalize before 7 full days.",
                    "ERR_COOLING_PERIOD_NOT_ELAPSED",
                    http_status=409
                )

        StateMachineValidator.validate_transition(subscriber.state, SubscriberState.PORTED_OUT)

    @classmethod
    def apply_finalization(cls, subscriber: Subscriber) -> None:
        subscriber.state = SubscriberState.PORTED_OUT
        subscriber.is_consumption_active = False
