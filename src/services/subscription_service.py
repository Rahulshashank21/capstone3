import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set

from src.domain.models import (
    Subscriber, SubscriberState, PlanVersion, PlanType, AuditLog, Role,
    BillingRecord, PortOutRecord,
    InvalidSubscriberStateException, ActivationFailedException,
    PlanImmutableException, ProRataCalculationException,
    PlanChangeTenureException, CoolingPeriodExpiredException,
    ConsumptionHaltedException, UnauthorizedException, DomainException
)
from src.domain.rules import StateMachineValidator, ProRataCalculator, ActivationRuleEngine, ActivationPolicy, PlanPolicy
from src.repositories.subscriber_repository import SubscriberRepository
from src.repositories.plan_repository import PlanRepository
from src.repositories.audit_repository import AuditRepository
from src.repositories.billing_repository import BillingRepository

class PlanDictWrapper(dict):
    """Dictionary-like wrapper synchronizing dict mutations with PlanRepository."""
    def __init__(self, plan_repo: PlanRepository):
        super().__init__()
        self.plan_repo = plan_repo

    def __setitem__(self, key: str, value: PlanVersion):
        super().__setitem__(key, value)
        self.plan_repo.save(value)

    def __getitem__(self, key: str) -> PlanVersion:
        p = self.plan_repo.find_latest(key)
        if p is not None:
            return p
        return super().__getitem__(key)

    def get(self, key: str, default=None):
        p = self.plan_repo.find_latest(key)
        if p is not None:
            return p
        return super().get(key, default)

    def values(self):
        return self.plan_repo.list_all_latest()

    def items(self):
        return [(p.plan_id, p) for p in self.plan_repo.list_all_latest()]

    def __contains__(self, key):
        return self.plan_repo.find_latest(key) is not None

class SubscriptionService:
    def __init__(
        self,
        subscriber_repo: Optional[SubscriberRepository] = None,
        plan_repo: Optional[PlanRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
        billing_repo: Optional[BillingRepository] = None
    ):
        self.subscriber_repo = subscriber_repo or SubscriberRepository()
        self.plan_repo = plan_repo or PlanRepository()
        self.audit_repo = audit_repo or AuditRepository()
        self.billing_repo = billing_repo or BillingRepository()
        self.valid_dealers = {"DEALER_001", "DEALER_002", "OFFICIAL_WEB"}

        # Backwards compatibility attributes
        self.subscribers: Dict[str, Subscriber] = self.subscriber_repo._subscribers
        self.plans = PlanDictWrapper(self.plan_repo)
        self.audit_logs: List[AuditLog] = self.audit_repo._logs
        self.active_numbers: Set[str] = self.subscriber_repo._active_mobile_numbers

    # --- Plan Catalog Management (AC-03) ---

    def create_plan(
        self,
        plan_id: str,
        name: str,
        plan_type: PlanType,
        monthly_rent: Decimal,
        validity_days: int,
        data_gb: int,
        voice_minutes: int = -1,
        sms_count: int = -1,
        min_tenure_days: int = 0,
        is_published: bool = False
    ) -> PlanVersion:
        PlanPolicy.validate_plan_attributes(plan_id, name, plan_type, monthly_rent, validity_days, data_gb)
        
        # Determine next version
        existing = self.plan_repo.find_latest(plan_id)
        version = (existing.version + 1) if existing else 1

        plan = PlanVersion(
            plan_id=plan_id,
            version=version,
            name=name,
            plan_type=plan_type,
            monthly_rent=monthly_rent,
            validity_days=validity_days,
            data_gb=data_gb,
            voice_minutes=voice_minutes,
            sms_count=sms_count,
            min_tenure_days=min_tenure_days,
            is_published=is_published
        )
        return self.plan_repo.save(plan)

    def publish_plan(self, plan_id: str, version: Optional[int] = None) -> PlanVersion:
        plan = self.plan_repo.find_by_version(plan_id, version) if version else self.plan_repo.find_latest(plan_id)
        if not plan:
            raise DomainException(f"Plan '{plan_id}' not found", "ERR_PLAN_NOT_FOUND")

        published_plan = PlanVersion(
            plan_id=plan.plan_id,
            version=plan.version,
            name=plan.name,
            plan_type=plan.plan_type,
            monthly_rent=plan.monthly_rent,
            validity_days=plan.validity_days,
            data_gb=plan.data_gb,
            voice_minutes=plan.voice_minutes,
            sms_count=plan.sms_count,
            min_tenure_days=plan.min_tenure_days,
            is_published=True
        )
        return self.plan_repo.save(published_plan)

    def get_plan(self, plan_id: str, version: Optional[int] = None) -> PlanVersion:
        plan = self.plan_repo.find_by_version(plan_id, version) if version else self.plan_repo.find_latest(plan_id)
        if not plan:
            raise DomainException(f"Plan '{plan_id}' not found", "ERR_PLAN_NOT_FOUND")
        return plan

    def list_plans(self, published_only: bool = True) -> List[PlanVersion]:
        if published_only:
            return self.plan_repo.list_published()
        return self.plan_repo.list_all_latest()

    # --- Subscriber Registration & Activation (AC-01, AC-08) ---

    def register_subscriber(self, mobile_number: str, identity_proof_ref: str, preferred_plan_type: PlanType) -> Subscriber:
        subscriber_id = f"SUB-{uuid.uuid4().hex[:8]}"
        subscriber = Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref=identity_proof_ref,
            preferred_plan_type=preferred_plan_type,
            state=SubscriberState.PENDING_KYC
        )
        self.subscriber_repo.save(subscriber)
        return subscriber

    def activate_subscriber(
        self,
        subscriber_id: str,
        kyc_status: str,
        dealer_code: str,
        mnp_status: str,
        initial_plan_id: str
    ) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        StateMachineValidator.validate_transition(sub.state, SubscriberState.ACTIVE)

        ActivationPolicy.validate_activation(
            kyc_status=kyc_status,
            dealer_code=dealer_code,
            mnp_status=mnp_status,
            mobile_number=sub.mobile_number,
            active_numbers=self.subscriber_repo.get_active_numbers(),
            valid_dealers=list(self.valid_dealers)
        )

        plan = self.plan_repo.find_latest(initial_plan_id)
        if not plan:
            raise ActivationFailedException("Plan does not exist", "ERR_PLAN_NOT_FOUND")

        sub.state = SubscriberState.ACTIVE
        sub.current_plan_id = initial_plan_id
        sub.plan_activated_at = datetime.now(timezone.utc)
        sub.is_consumption_active = True
        self.subscriber_repo.save(sub)

        # Audit activation
        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:8]}",
            actor=dealer_code,
            role=Role.DEALER,
            action="SUBSCRIBER_ACTIVATED",
            reason_code="ACTIVATION_SUCCESS",
            details=f"Subscriber {sub.mask_pii()['subscriber_id']} successfully activated on plan {initial_plan_id}"
        ))

        return sub

    # --- CSR Overrides (AC-09) ---

    def csr_override_activation(
        self,
        subscriber_id: str,
        initial_plan_id: str,
        actor_id: str,
        reason_code: str
    ) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        StateMachineValidator.validate_transition(sub.state, SubscriberState.ACTIVE)

        plan = self.plan_repo.find_latest(initial_plan_id)
        if not plan:
            raise ActivationFailedException("Plan does not exist", "ERR_PLAN_NOT_FOUND")

        sub.state = SubscriberState.ACTIVE
        sub.current_plan_id = initial_plan_id
        sub.plan_activated_at = datetime.now(timezone.utc)
        sub.is_consumption_active = True
        self.subscriber_repo.save(sub)

        audit = AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:8]}",
            actor=actor_id,
            role=Role.CSR,
            action="CSR_ACTIVATION_OVERRIDE",
            reason_code=reason_code,
            details=f"Overrode activation failure for subscriber {subscriber_id}"
        )
        self.audit_repo.append(audit)
        return sub

    def csr_override_plan_change(
        self,
        subscriber_id: str,
        new_plan_id: str,
        actor_id: str,
        reason_code: str,
        days_used: int = 0,
        cycle_days: int = 30
    ) -> Dict[str, Any]:
        return self.change_plan(
            subscriber_id=subscriber_id,
            new_plan_id=new_plan_id,
            days_used=days_used,
            cycle_days=cycle_days,
            bypass_tenure=True,
            actor_id=actor_id,
            override_reason=reason_code
        )

    # --- Plan Change & Pro-Rata Billing (AC-04, AC-05) ---

    def change_plan(
        self,
        subscriber_id: str,
        new_plan_id: str,
        days_used: int = 0,
        cycle_days: int = 30,
        bypass_tenure: bool = False,
        actor_id: Optional[str] = None,
        override_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        sub = self.get_subscriber(subscriber_id)
        if sub.state != SubscriberState.ACTIVE:
            raise InvalidSubscriberStateException("Subscriber must be ACTIVE to change plans", "ERR_NOT_ACTIVE")

        current_plan = self.plan_repo.find_latest(sub.current_plan_id)
        new_plan = self.plan_repo.find_latest(new_plan_id)
        if not current_plan or not new_plan:
            raise DomainException("Plan configuration error", "ERR_PLAN_NOT_FOUND")

        # Tenure validation (AC-04)
        if not bypass_tenure:
            PlanPolicy.validate_tenure_requirement(current_plan, sub.plan_activated_at)

        pro_rata_charge = Decimal("0.00")
        effective_date = datetime.now(timezone.utc)

        if current_plan.plan_type == PlanType.POSTPAID:
            pro_rata_charge = ProRataCalculator.calculate(
                old_rent=current_plan.monthly_rent,
                new_rent=new_plan.monthly_rent,
                days_used=days_used,
                cycle_days=cycle_days
            )
            # Record billing transaction
            self.billing_repo.append(BillingRecord(
                record_id=f"BIL-{uuid.uuid4().hex[:8]}",
                subscriber_id=sub.subscriber_id,
                plan_id=new_plan_id,
                amount=pro_rata_charge,
                description=f"Mid-cycle migration {current_plan.plan_id} -> {new_plan.plan_id}",
                days_used=days_used,
                cycle_days=cycle_days
            ))

        sub.current_plan_id = new_plan_id
        sub.plan_activated_at = effective_date
        self.subscriber_repo.save(sub)

        # Audit plan change
        action_name = "PLAN_CHANGE_CSR_OVERRIDE" if bypass_tenure else "PLAN_CHANGE"
        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:8]}",
            actor=actor_id or sub.subscriber_id,
            role=Role.CSR if bypass_tenure else Role.SUBSCRIBER,
            action=action_name,
            reason_code=override_reason or "SUBSCRIBER_REQUEST",
            details=f"Plan changed from {current_plan.plan_id} to {new_plan.plan_id}. Pro-rata charge: ${pro_rata_charge}"
        ))

        return {
            "subscriber_id": sub.subscriber_id,
            "old_plan_id": current_plan.plan_id,
            "new_plan_id": new_plan.plan_id,
            "pro_rata_charge": pro_rata_charge,
            "effective_date": effective_date.isoformat()
        }

    # --- Suspension & Consumption Halting (AC-06) ---

    def suspend_subscriber(self, subscriber_id: str, reason: str = "REQUESTED_BY_USER") -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        StateMachineValidator.validate_transition(sub.state, SubscriberState.SUSPENDED)
        sub.state = SubscriberState.SUSPENDED
        sub.is_consumption_active = False
        self.subscriber_repo.save(sub)

        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:8]}",
            actor=sub.subscriber_id,
            role=Role.SUBSCRIBER,
            action="SUBSCRIBER_SUSPENDED",
            reason_code=reason,
            details="Subscriber entered SUSPENDED state; consumption halted"
        ))
        return sub

    def reactivate_subscriber(self, subscriber_id: str) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        StateMachineValidator.validate_transition(sub.state, SubscriberState.ACTIVE)
        sub.state = SubscriberState.ACTIVE
        sub.is_consumption_active = True
        self.subscriber_repo.save(sub)

        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:8]}",
            actor=sub.subscriber_id,
            role=Role.SUBSCRIBER,
            action="SUBSCRIBER_REACTIVATED",
            reason_code="SERVICE_RESUMED",
            details="Subscriber restored to ACTIVE state; consumption resumed"
        ))
        return sub

    def assert_can_consume(self, subscriber_id: str) -> bool:
        sub = self.get_subscriber(subscriber_id)
        if sub.state != SubscriberState.ACTIVE or not sub.is_consumption_active:
            raise ConsumptionHaltedException(
                f"Network consumption halted for subscriber in state {sub.state}",
                "ERR_CONSUMPTION_HALTED"
            )
        return True

    # --- Port-Out Cooling Period State Machine (AC-07) ---

    def initiate_port_out(self, subscriber_id: str, recipient_operator: str = "REC_OPERATOR_01") -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        StateMachineValidator.validate_transition(sub.state, SubscriberState.PORT_OUT_REQUESTED)
        sub.state = SubscriberState.PORT_OUT_REQUESTED
        sub.port_out_requested_at = datetime.now(timezone.utc)
        self.subscriber_repo.save(sub)

        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:8]}",
            actor=sub.subscriber_id,
            role=Role.SUBSCRIBER,
            action="PORT_OUT_INITIATED",
            reason_code="REGULATORY_COOLING_STARTED",
            details=f"Port-out initiated to {recipient_operator}. 7-day cooling period active."
        ))
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
        self.subscriber_repo.save(sub)

        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:8]}",
            actor=sub.subscriber_id,
            role=Role.SUBSCRIBER,
            action="PORT_OUT_CANCELLED",
            reason_code="CUSTOMER_RETENTION",
            details="Subscriber cancelled port-out request within 7-day window. Restored to ACTIVE."
        ))
        return sub

    def finalize_port_out(self, subscriber_id: str) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        if sub.state != SubscriberState.PORT_OUT_REQUESTED:
            raise InvalidSubscriberStateException("Subscriber is not in PORT_OUT_REQUESTED state", "ERR_INVALID_STATE")

        StateMachineValidator.validate_transition(sub.state, SubscriberState.PORTED_OUT)
        sub.state = SubscriberState.PORTED_OUT
        sub.is_consumption_active = False
        self.subscriber_repo.save(sub)

        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:8]}",
            actor="SYSTEM_MNP_JOB",
            role=Role.ADMIN,
            action="PORT_OUT_FINALIZED",
            reason_code="COOLING_PERIOD_ELAPSED",
            details=f"Port-out finalized for {sub.mask_pii()['subscriber_id']}. Mobile number released."
        ))
        return sub

    # --- Query helpers ---

    def get_subscriber(self, subscriber_id: str) -> Subscriber:
        sub = self.subscriber_repo.find_by_id(subscriber_id)
        if not sub:
            raise DomainException("Subscriber not found", "ERR_SUBSCRIBER_NOT_FOUND")
        return sub
