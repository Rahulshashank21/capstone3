from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from src.domain.models import (
    Subscriber, SubscriberState, PlanVersion, PlanType,
    InvalidSubscriberStateException, ActivationFailedException, ProRataCalculationException
)

class StateMachineValidator:
    VALID_TRANSITIONS: Dict[SubscriberState, List[SubscriberState]] = {
        SubscriberState.PENDING_KYC: [SubscriberState.ACTIVE, SubscriberState.TERMINATED],
        SubscriberState.ACTIVE: [SubscriberState.SUSPENDED, SubscriberState.PORT_OUT_REQUESTED, SubscriberState.TERMINATED],
        SubscriberState.SUSPENDED: [SubscriberState.ACTIVE, SubscriberState.TERMINATED],
        SubscriberState.PORT_OUT_REQUESTED: [SubscriberState.ACTIVE, SubscriberState.PORTED_OUT, SubscriberState.TERMINATED],
        SubscriberState.PORTED_OUT: [],
        SubscriberState.TERMINATED: []
    }

    @classmethod
    def validate_transition(cls, current: SubscriberState, target: SubscriberState) -> None:
        allowed = cls.VALID_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise InvalidSubscriberStateException(
                f"Invalid lifecycle transition from {current} to {target}",
                "ERR_INVALID_STATE_TRANSITION"
            )

class ProRataCalculator:
    @staticmethod
    def calculate(old_rent: Decimal, new_rent: Decimal, days_used: int, cycle_days: int) -> Decimal:
        if cycle_days <= 0:
            raise ProRataCalculationException("Billing cycle days must be greater than zero", "ERR_INVALID_CYCLE_DAYS")
        if days_used < 0 or days_used > cycle_days:
            raise ProRataCalculationException("Days used must be within cycle duration", "ERR_INVALID_DAYS_USED")
        
        days_used_dec = Decimal(str(days_used))
        cycle_days_dec = Decimal(str(cycle_days))
        days_remaining_dec = cycle_days_dec - days_used_dec

        old_charge = (days_used_dec / cycle_days_dec) * old_rent
        new_charge = (days_remaining_dec / cycle_days_dec) * new_rent
        total = (old_charge + new_charge).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if total < Decimal("0.00"):
            raise ProRataCalculationException("Pro-rata charges invariant violated: total < 0", "ERR_NEGATIVE_PRO_RATA")
        
        return total

class ActivationRuleEngine:
    @staticmethod
    def evaluate(kyc_status: str, dealer_code: str, mnp_status: str, valid_dealers: List[str]) -> None:
        if kyc_status != "VERIFIED":
            raise ActivationFailedException("KYC identity proof verification failed", "ERR_KYC_FAILED")
        if dealer_code not in valid_dealers:
            raise ActivationFailedException("Invalid dealer code provided", "ERR_INVALID_DEALER")
        if mnp_status == "REJECTED":
            raise ActivationFailedException("MNP porting validation failed downstream", "ERR_MNP_REJECTED")
