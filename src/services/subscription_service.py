import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from src.domain.models import (
    Subscriber, SubscriberState, PlanVersion, PlanType, AuditLog, Role,
    InvalidSubscriberStateException, ActivationFailedException, DomainException
)
from src.domain.rules import StateMachineValidator, ProRataCalculator, ActivationRuleEngine

class SubscriptionService:
    def __init__(self):
        self.subscribers: Dict[str, Subscriber] = {}
        self.plans: Dict[str, PlanVersion] = {}
        self.audit_logs: List[AuditLog] = []
        self.active_numbers: set = set()
        self.valid_dealers = {"DEALER_001", "DEALER_002", "OFFICIAL_WEB"}

    def register_subscriber(self, mobile_number: str, identity_proof_ref: str, preferred_plan_type: PlanType) -> Subscriber:
        subscriber_id = f"SUB-{uuid.uuid4().hex[:8]}"
        subscriber = Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref=identity_proof_ref,
            preferred_plan_type=preferred_plan_type,
            state=SubscriberState.PENDING_KYC
        )
        self.subscribers[subscriber_id] = subscriber
        return subscriber

    def activate_subscriber(self, subscriber_id: str, kyc_status: str, dealer_code: str, mnp_status: str, initial_plan_id: str) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        StateMachineValidator.validate_transition(sub.state, SubscriberState.ACTIVE)

        if sub.mobile_number in self.active_numbers:
            raise ActivationFailedException("Mobile number already holds an ACTIVE subscription", "ERR_DUPLICATE_ACTIVE_NUMBER")

        ActivationRuleEngine.evaluate(kyc_status, dealer_code, mnp_status, list(self.valid_dealers))

        plan = self.plans.get(initial_plan_id)
        if not plan:
            raise ActivationFailedException("Plan does not exist", "ERR_PLAN_NOT_FOUND")

        sub.state = SubscriberState.ACTIVE
        sub.current_plan_id = initial_plan_id
        sub.plan_activated_at = datetime.now(timezone.utc)
        self.active_numbers.add(sub.mobile_number)
        return sub

    def csr_override_activation(self, subscriber_id: str, initial_plan_id: str, actor_id: str, reason_code: str) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        StateMachineValidator.validate_transition(sub.state, SubscriberState.ACTIVE)
        
        plan = self.plans.get(initial_plan_id)
        if not plan:
            raise ActivationFailedException("Plan does not exist", "ERR_PLAN_NOT_FOUND")

        sub.state = SubscriberState.ACTIVE
        sub.current_plan_id = initial_plan_id
        sub.plan_activated_at = datetime.now(timezone.utc)
        self.active_numbers.add(sub.mobile_number)

        audit = AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:8]}",
            actor=actor_id,
            role=Role.CSR,
            action="CSR_ACTIVATION_OVERRIDE",
            reason_code=reason_code,
            details=f"Overrode activation failure for subscriber {subscriber_id}"
        )
        self.audit_logs.append(audit)
        return sub

    def change_plan(self, subscriber_id: str, new_plan_id: str, days_used: int = 0, cycle_days: int = 30) -> Dict[str, Any]:
        sub = self.get_subscriber(subscriber_id)
        if sub.state != SubscriberState.ACTIVE:
            raise InvalidSubscriberStateException("Subscriber must be ACTIVE to change plans", "ERR_NOT_ACTIVE")

        current_plan = self.plans.get(sub.current_plan_id)
        new_plan = self.plans.get(new_plan_id)
        if not current_plan or not new_plan:
            raise DomainException("Plan configuration error", "ERR_PLAN_NOT_FOUND")

        pro_rata_charge = Decimal("0.00")
        effective_date = datetime.now(timezone.utc)

        if current_plan.plan_type == PlanType.POSTPAID:
            pro_rata_charge = ProRataCalculator.calculate(
                old_rent=current_plan.monthly_rent,
                new_rent=new_plan.monthly_rent,
                days_used=days_used,
                cycle_days=cycle_days
            )
        
        sub.current_plan_id = new_plan_id
        sub.plan_activated_at = effective_date

        return {
            "subscriber_id": sub.subscriber_id,
            "old_plan_id": current_plan.plan_id,
            "new_plan_id": new_plan.plan_id,
            "pro_rata_charge": pro_rata_charge,
            "effective_date": effective_date.isoformat()
        }

    def initiate_port_out(self, subscriber_id: str) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        StateMachineValidator.validate_transition(sub.state, SubscriberState.PORT_OUT_REQUESTED)
        sub.state = SubscriberState.PORT_OUT_REQUESTED
        sub.port_out_requested_at = datetime.now(timezone.utc)
        return sub

    def cancel_port_out(self, subscriber_id: str) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        if sub.state != SubscriberState.PORT_OUT_REQUESTED:
            raise InvalidSubscriberStateException("Subscriber is not in PORT_OUT_REQUESTED state", "ERR_INVALID_STATE")
        
        if sub.port_out_requested_at and (datetime.now(timezone.utc) - sub.port_out_requested_at) > timedelta(days=7):
            raise InvalidSubscriberStateException("Cooling period of 7 days has expired", "ERR_COOLING_PERIOD_EXPIRED")

        StateMachineValidator.validate_transition(sub.state, SubscriberState.ACTIVE)
        sub.state = SubscriberState.ACTIVE
        sub.port_out_requested_at = None
        return sub

    def get_subscriber(self, subscriber_id: str) -> Subscriber:
        sub = self.subscribers.get(subscriber_id)
        if not sub:
            raise DomainException("Subscriber not found", "ERR_SUBSCRIBER_NOT_FOUND")
        return sub
