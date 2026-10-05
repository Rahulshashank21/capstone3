import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set

from src.domain.models import (
    Subscriber, SubscriberState, PlanVersion, PlanType, AuditLog, Role,
    BillingRecord, PortOutRecord, RejectionRecord,
    InvalidSubscriberStateException, ActivationFailedException,
    PlanImmutableException, ProRataCalculationException,
    PlanChangeTenureException, CoolingPeriodExpiredException,
    ConsumptionHaltedException, UnauthorizedException, DomainException
)
from src.domain.rules import (
    StateMachineValidator, ProRataCalculator, ActivationRuleEngine,
    ActivationPolicy, PlanPolicy, PlanChangePolicy, PortOutPolicy, SuspensionPolicy, CSROverridePolicy
)
from src.repositories.subscriber_repository import SubscriberRepository
from src.repositories.plan_repository import PlanRepository
from src.repositories.audit_repository import AuditRepository
from src.repositories.billing_repository import BillingRepository
from src.repositories.rejection_repository import RejectionRepository

class PlanCatalogProxy(dict):
    """Dictionary-compatible proxy delegating strictly to PlanRepository public methods under locks."""
    def __init__(self, plan_repo: PlanRepository):
        super().__init__()
        self._plan_repo = plan_repo

    def __setitem__(self, key: str, value: PlanVersion):
        self._plan_repo.save(value)

    def __getitem__(self, key: str) -> PlanVersion:
        p = self._plan_repo.find_latest(key)
        if p is None:
            raise KeyError(key)
        return p

    def get(self, key: str, default=None):
        p = self._plan_repo.find_latest(key)
        return p if p is not None else default

    def values(self):
        return self._plan_repo.list_all_latest()

    def items(self):
        return [(p.plan_id, p) for p in self._plan_repo.list_all_latest()]

    def __contains__(self, key):
        return self._plan_repo.find_latest(key) is not None

    def __iter__(self):
        return iter(p.plan_id for p in self._plan_repo.list_all_latest())

    def __len__(self):
        return len(self._plan_repo.list_all_latest())

class SubscriptionService:
    def __init__(
        self,
        subscriber_repo: Optional[SubscriberRepository] = None,
        plan_repo: Optional[PlanRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
        billing_repo: Optional[BillingRepository] = None,
        rejection_repo: Optional[Any] = None,
        port_out_repo: Optional[Any] = None,
        transition_repo: Optional[Any] = None
    ):
        self.subscriber_repo = subscriber_repo or SubscriberRepository()
        self.plan_repo = plan_repo or PlanRepository()
        self.audit_repo = audit_repo or AuditRepository()
        self.billing_repo = billing_repo or BillingRepository()
        self.rejection_repo = rejection_repo or RejectionRepository()
        self.port_out_repo = port_out_repo
        self.transition_repo = transition_repo
        self.valid_dealers = {"DEALER_001", "DEALER_002", "OFFICIAL_WEB"}
        self.plans = PlanCatalogProxy(self.plan_repo)

    @property
    def audit_logs(self) -> List[AuditLog]:
        return self.audit_repo.list_all()

    @property
    def subscribers(self) -> Dict[str, Subscriber]:
        return {s.subscriber_id: s for s in self.subscriber_repo.list_all()}

    @property
    def active_numbers(self) -> Set[str]:
        return self.subscriber_repo.get_active_numbers()

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
        # Prevent duplicate pending KYC registrations for the same number
        pending_existing = [s for s in self.subscriber_repo.find_by_mobile(mobile_number) if s.state == SubscriberState.PENDING_KYC]
        if pending_existing:
            raise DomainException(
                f"Mobile number {mobile_number} already has a pending registration awaiting KYC verification",
                "ERR_DUPLICATE_MOBILE_NUMBER",
                http_status=409
            )

        subscriber_id = f"SUB-{uuid.uuid4().hex}"
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

        try:
            ActivationPolicy.validate_activation(
                kyc_status=kyc_status,
                dealer_code=dealer_code,
                mnp_status=mnp_status,
                mobile_number=sub.mobile_number,
                active_numbers=self.subscriber_repo.get_active_numbers(),
                valid_dealers=list(self.valid_dealers)
            )
        except ActivationFailedException as e:
            rej_id = f"REJ-{uuid.uuid4().hex}"
            self.rejection_repo.append(RejectionRecord(
                rejection_id=rej_id,
                subscriber_id=sub.subscriber_id,
                stage="ACTIVATION",
                rule=e.reason_code,
                reason_code=e.reason_code,
                details=str(e),
                timestamp=datetime.now(timezone.utc)
            ))
            e.rejection_id = rej_id
            raise e

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
            log_id=f"AUD-{uuid.uuid4().hex}",
            actor=dealer_code,
            role=Role.DEALER,
            action="SUBSCRIBER_ACTIVATED",
            reason_code="ACTIVATION_SUCCESS",
            details=f"Subscriber {sub.mask_pii()['masked_subscriber_id']} successfully activated on plan {initial_plan_id}",
            masked_subscriber_id=sub.mask_pii()["masked_subscriber_id"]
        ))

        return sub

    # --- CSR Overrides (AC-09) ---

    def csr_override_activation(
        self,
        subscriber_id: str,
        initial_plan_id: str,
        actor_id: str,
        reason_code: str,
        rejection_id: Optional[str] = None
    ) -> Subscriber:
        CSROverridePolicy.validate_override_request(Role.CSR, reason_code, rejection_id)
        
        # Link and validate rejection record
        effective_rejection_id = rejection_id
        if effective_rejection_id:
            rejection = self.rejection_repo.find_by_id(effective_rejection_id)
            if not rejection or rejection.subscriber_id != subscriber_id:
                raise DomainException(
                    f"Rejection record '{effective_rejection_id}' does not exist or does not match subscriber '{subscriber_id}'",
                    "ERR_INVALID_REJECTION_ID",
                    http_status=404
                )
        else:
            prior_rejections = self.rejection_repo.list_by_subscriber(subscriber_id)
            if not prior_rejections:
                raise DomainException(
                    "rejection_id or prior activation rejection record is required for CSR override",
                    "ERR_REJECTION_REQUIRED",
                    http_status=422
                )
            effective_rejection_id = prior_rejections[0].rejection_id

        sub = self.get_subscriber(subscriber_id)
        StateMachineValidator.validate_transition(sub.state, SubscriberState.ACTIVE)

        # Enforce active mobile number exclusivity (NFR-08)
        if sub.mobile_number in self.subscriber_repo.get_active_numbers():
            raise ActivationFailedException(
                "Mobile number already holds an ACTIVE subscription on the network",
                "ERR_DUPLICATE_ACTIVE_NUMBER"
            )

        plan = self.plan_repo.find_latest(initial_plan_id)
        if not plan:
            raise ActivationFailedException("Plan does not exist", "ERR_PLAN_NOT_FOUND")

        sub.state = SubscriberState.ACTIVE
        sub.current_plan_id = initial_plan_id
        now = datetime.now(timezone.utc)
        sub.plan_activated_at = now
        if not sub.initial_activated_at:
            sub.initial_activated_at = now
        sub.is_consumption_active = True
        self.subscriber_repo.save(sub)

        audit = AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex}",
            actor=actor_id,
            role=Role.CSR,
            action="CSR_ACTIVATION_OVERRIDE",
            reason_code=reason_code,
            details=f"Overrode activation failure ({effective_rejection_id}) for subscriber {sub.mask_pii()['masked_subscriber_id']}",
            masked_subscriber_id=sub.mask_pii()["masked_subscriber_id"],
            timestamp=now
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
        immediate_pro_rata: bool = True,
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

        # Validate migration policy, published status, identical plan, family compatibility, tenure, and billing
        eval_result = PlanChangePolicy.evaluate_migration(
            current_plan=current_plan,
            new_plan=new_plan,
            plan_activated_at=sub.plan_activated_at,
            initial_activated_at=sub.initial_activated_at,
            days_used=days_used,
            cycle_days=cycle_days,
            immediate_pro_rata=immediate_pro_rata,
            bypass_tenure=bypass_tenure
        )

        immediate_apply = eval_result.get("immediate_apply", True)
        pro_rata_charge = eval_result["charge"]
        effective_date = eval_result["effective_from"]

        if immediate_apply:
            if current_plan.plan_type == PlanType.POSTPAID:
                # Record billing transaction
                self.billing_repo.append(BillingRecord(
                    record_id=f"BIL-{uuid.uuid4().hex}",
                    subscriber_id=sub.subscriber_id,
                    plan_id=new_plan_id,
                    amount=pro_rata_charge,
                    description=f"Mid-cycle migration {current_plan.plan_id} -> {new_plan.plan_id}",
                    days_used=days_used,
                    cycle_days=cycle_days
                ))

            sub.current_plan_id = new_plan_id
            sub.plan_activated_at = effective_date
            sub.pending_plan_id = None
            sub.pending_plan_effective_from = None
        else:
            # AC-04 Next cycle migration
            sub.pending_plan_id = new_plan_id
            sub.pending_plan_effective_from = effective_date

        self.subscriber_repo.save(sub)

        # Audit plan change
        action_name = "PLAN_CHANGE_CSR_OVERRIDE" if bypass_tenure else (
            "PLAN_CHANGE" if immediate_apply else "PLAN_CHANGE_SCHEDULED"
        )
        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex}",
            actor=actor_id or sub.subscriber_id,
            role=Role.CSR if bypass_tenure else Role.SUBSCRIBER,
            action=action_name,
            reason_code=override_reason or "SUBSCRIBER_REQUEST",
            details=f"Plan migration {current_plan.plan_id} -> {new_plan.plan_id} (effective: {eval_result['effective_mode']}). Charge: ${pro_rata_charge}",
            masked_subscriber_id=sub.mask_pii()["masked_subscriber_id"]
        ))

        return {
            "subscriber_id": sub.subscriber_id,
            "old_plan_id": current_plan.plan_id,
            "new_plan_id": new_plan.plan_id,
            "pro_rata_charge": pro_rata_charge,
            "effective_date": effective_date.isoformat(),
            "effective_mode": eval_result.get("effective_mode", "IMMEDIATE")
        }

    def apply_cycle_boundary_migrations(self, as_of_time: Optional[datetime] = None) -> List[Subscriber]:
        """Processes all scheduled plan changes whose cycle boundary has arrived (AC-04)."""
        now = as_of_time or datetime.now(timezone.utc)
        migrated = []
        for sub in self.subscriber_repo.list_all():
            if sub.pending_plan_id and sub.pending_plan_effective_from and sub.pending_plan_effective_from <= now:
                old_plan_id = sub.current_plan_id
                sub.current_plan_id = sub.pending_plan_id
                sub.plan_activated_at = sub.pending_plan_effective_from
                sub.pending_plan_id = None
                sub.pending_plan_effective_from = None
                self.subscriber_repo.save(sub)
                migrated.append(sub)
                self.audit_repo.append(AuditLog(
                    log_id=f"AUD-{uuid.uuid4().hex}",
                    actor="BILLING_CYCLE_SCHEDULER",
                    role=Role.ADMIN,
                    action="PLAN_CHANGE_CYCLE_BOUNDARY",
                    reason_code="CYCLE_BOUNDARY_TRANSITION",
                    details=f"Pending plan {sub.current_plan_id} applied at cycle boundary from {old_plan_id}",
                    masked_subscriber_id=sub.mask_pii()["masked_subscriber_id"],
                    timestamp=now
                ))
        return migrated

    # --- Suspension & Consumption Halting (AC-06) ---

    # --- Suspension & Consumption Halting (AC-06) ---

    def suspend_subscriber(self, subscriber_id: str, reason: str = "REQUESTED_BY_USER", actor: Optional[str] = None, role: Role = Role.SUBSCRIBER) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        SuspensionPolicy.validate_suspension(sub, reason)
        SuspensionPolicy.apply_suspension(sub, reason)
        self.subscriber_repo.save(sub)

        now = datetime.now(timezone.utc)
        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex}",
            actor=actor or sub.subscriber_id,
            role=role,
            action="SUBSCRIBER_SUSPENDED",
            reason_code=reason,
            details=f"Subscriber entered SUSPENDED state from {sub.previous_state.value if sub.previous_state else 'ACTIVE'}; consumption halted",
            masked_subscriber_id=sub.mask_pii()["masked_subscriber_id"],
            timestamp=now
        ))
        return sub

    def reactivate_subscriber(self, subscriber_id: str, actor: Optional[str] = None, role: Role = Role.SUBSCRIBER) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        # AC-06: Strict guard - only SUSPENDED subscribers can be reactivated
        SuspensionPolicy.validate_reactivation(sub)
        SuspensionPolicy.apply_reactivation(sub)
        self.subscriber_repo.save(sub)

        now = datetime.now(timezone.utc)
        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex}",
            actor=actor or sub.subscriber_id,
            role=role,
            action="SUBSCRIBER_REACTIVATED",
            reason_code="SERVICE_RESUMED",
            details="Subscriber restored to prior state; consumption resumed",
            masked_subscriber_id=sub.mask_pii()["masked_subscriber_id"],
            timestamp=now
        ))
        return sub

    def assert_can_consume(self, subscriber_id: str) -> bool:
        sub = self.get_subscriber(subscriber_id)
        SuspensionPolicy.assert_consumption_permitted(sub)
        return True

    # --- Port-Out Cooling Period State Machine (AC-07) ---

    def initiate_port_out(self, subscriber_id: str, recipient_operator: str = "REC_OPERATOR_01") -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        validated_op = PortOutPolicy.validate_initiation(sub, recipient_operator)
        now = datetime.now(timezone.utc)
        PortOutPolicy.apply_initiation(sub, now)
        self.subscriber_repo.save(sub)

        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex}",
            actor=sub.subscriber_id,
            role=Role.SUBSCRIBER,
            action="PORT_OUT_INITIATED",
            reason_code="REGULATORY_COOLING_STARTED",
            details=f"Port-out initiated to {validated_op.value}. 7-day cooling period active.",
            masked_subscriber_id=sub.mask_pii()["masked_subscriber_id"],
            timestamp=now
        ))
        return sub

    def cancel_port_out(self, subscriber_id: str) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        now = datetime.now(timezone.utc)
        PortOutPolicy.validate_cancellation(sub, current_time=now)
        PortOutPolicy.apply_cancellation(sub)
        self.subscriber_repo.save(sub)

        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex}",
            actor=sub.subscriber_id,
            role=Role.SUBSCRIBER,
            action="PORT_OUT_CANCELLED",
            reason_code="CUSTOMER_RETENTION",
            details="Subscriber cancelled port-out request within 7-day window. Restored to ACTIVE.",
            masked_subscriber_id=sub.mask_pii()["masked_subscriber_id"],
            timestamp=now
        ))
        return sub

    def finalize_port_out(
        self,
        subscriber_id: str,
        force_override: bool = False,
        enforce_cooling_period: bool = True,
        caller_role: Optional[Role] = None,
        override_reason: Optional[str] = None,
        actor: Optional[str] = None
    ) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        now = datetime.now(timezone.utc)
        if enforce_cooling_period:
            PortOutPolicy.validate_finalization(
                sub,
                current_time=now,
                force_override=force_override,
                caller_role=caller_role,
                override_reason=override_reason
            )
        else:
            StateMachineValidator.validate_transition(sub.state, SubscriberState.PORTED_OUT)
        PortOutPolicy.apply_finalization(sub)
        self.subscriber_repo.save(sub)

        action_name = "PORT_OUT_FINALIZED_OVERRIDE" if force_override else "PORT_OUT_FINALIZED"
        reason = override_reason if force_override else "COOLING_PERIOD_ELAPSED"
        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex}",
            actor=actor or "SYSTEM_MNP_JOB",
            role=caller_role or Role.ADMIN,
            action=action_name,
            reason_code=reason,
            details=f"Port-out finalized for {sub.mask_pii()['masked_subscriber_id']}. Mobile number released.",
            masked_subscriber_id=sub.mask_pii()["masked_subscriber_id"],
            timestamp=now
        ))
        return sub

    def terminate_subscriber(
        self,
        subscriber_id: str,
        reason: str = "ACCOUNT_CLOSED",
        actor: str = "CSR_SYSTEM",
        role: Role = Role.CSR
    ) -> Subscriber:
        sub = self.get_subscriber(subscriber_id)
        from_state = sub.state
        StateMachineValidator.validate_transition(from_state, SubscriberState.TERMINATED)
        sub.state = SubscriberState.TERMINATED
        sub.is_consumption_active = False
        self.subscriber_repo.save(sub)

        now = datetime.now(timezone.utc)
        self.audit_repo.append(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex}",
            actor=actor,
            role=role,
            action="SUBSCRIBER_TERMINATED",
            reason_code=f"TERMINATED_{reason.upper()}",
            details=f"Subscriber terminated from {from_state.value}. State: TERMINATED.",
            masked_subscriber_id=sub.mask_pii()["masked_subscriber_id"],
            timestamp=now
        ))
        return sub

    # --- Query helpers ---

    def get_subscriber(self, subscriber_id: str) -> Subscriber:
        sub = self.subscriber_repo.find_by_id(subscriber_id)
        if not sub:
            raise DomainException("Subscriber not found", "ERR_SUBSCRIBER_NOT_FOUND")
        return sub
