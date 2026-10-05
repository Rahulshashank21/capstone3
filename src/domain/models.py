import uuid
from decimal import Decimal
from enum import Enum
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

PII_SALT = "telcolane-pii-cryptographic-salt-2026"

def hash_pii(value: str) -> str:
    """Computes a salted cryptographic digest of sensitive PII data."""
    if not value:
        return ""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"{PII_SALT}:{value}").hex

def mask_mobile(number: str) -> str:
    """Masks mobile number: XXXXXX1234."""
    if not number:
        return "XXXX"
    clean = number.strip()
    if len(clean) >= 4:
        return "XXXXXX" + clean[-4:]
    return "XXXX"

def mask_subscriber_id(subscriber_id: str) -> str:
    """Masks subscriber ID for logs and audit records: SUB-XXXX1234."""
    if not subscriber_id:
        return "SUB-XXXX"
    parts = subscriber_id.split("-")
    if len(parts) >= 2 and len(parts[1]) >= 4:
        return f"SUB-XXXX{parts[1][-4:]}"
    return f"SUB-XXXX{subscriber_id[-4:]}"

class PlanType(str, Enum):
    PREPAID = "PREPAID"
    POSTPAID = "POSTPAID"

class SubscriberState(str, Enum):
    PENDING_KYC = "PENDING_KYC"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    PORT_OUT_REQUESTED = "PORT_OUT_REQUESTED"
    PORTED_OUT = "PORTED_OUT"

class Role(str, Enum):
    SUBSCRIBER = "SUBSCRIBER"
    CSR = "CSR"
    ADMIN = "ADMIN"
    DEALER = "DEALER"

class RecipientOperator(str, Enum):
    AIRTEL_IND = "AIRTEL_IND"
    JIO_IND = "JIO_IND"
    VI_IND = "VI_IND"
    REC_TELCO_5G = "REC_TELCO_5G"
    REC_OPERATOR_01 = "REC_OPERATOR_01"
    COMPETITOR_TELCO = "COMPETITOR_TELCO"

class MNPStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

# --- Domain Exceptions ---
class DomainException(Exception):
    def __init__(self, message: str, reason_code: str, http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.reason_code = reason_code
        self.http_status = http_status

class InvalidSubscriberStateException(DomainException):
    def __init__(self, message: str, reason_code: str = "ERR_INVALID_STATE_TRANSITION"):
        super().__init__(message, reason_code, http_status=409)

class PlanImmutableException(DomainException):
    def __init__(self, message: str, reason_code: str = "ERR_PLAN_IMMUTABLE"):
        super().__init__(message, reason_code, http_status=409)

class ActivationFailedException(DomainException):
    def __init__(self, message: str, reason_code: str):
        super().__init__(message, reason_code, http_status=422)

class ProRataCalculationException(DomainException):
    def __init__(self, message: str, reason_code: str):
        super().__init__(message, reason_code, http_status=422)

class PlanChangeTenureException(DomainException):
    def __init__(self, message: str, reason_code: str = "ERR_MINIMUM_TENURE_NOT_MET"):
        super().__init__(message, reason_code, http_status=422)

class CoolingPeriodExpiredException(InvalidSubscriberStateException):
    def __init__(self, message: str, reason_code: str = "ERR_COOLING_PERIOD_EXPIRED"):
        super().__init__(message, reason_code)

class ConsumptionHaltedException(DomainException):
    def __init__(self, message: str, reason_code: str = "ERR_CONSUMPTION_HALTED"):
        super().__init__(message, reason_code, http_status=403)

class UnauthorizedException(DomainException):
    def __init__(self, message: str, reason_code: str = "ERR_UNAUTHORIZED"):
        super().__init__(message, reason_code, http_status=403)

class NotFoundException(DomainException):
    def __init__(self, message: str, reason_code: str = "ERR_NOT_FOUND"):
        super().__init__(message, reason_code, http_status=404)

# --- Immutable Core Entities ---
@dataclass(frozen=True)
class PlanVersion:
    plan_id: str
    version: int
    name: str
    plan_type: PlanType
    monthly_rent: Decimal
    validity_days: int
    data_gb: int
    voice_minutes: int = -1
    sms_count: int = -1
    min_tenure_days: int = 0
    is_published: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def validate_immutability(self) -> None:
        if self.is_published:
            raise PlanImmutableException(
                f"Cannot modify published plan version '{self.plan_id}:v{self.version}'",
                "ERR_PLAN_IMMUTABLE"
            )

@dataclass(frozen=True)
class AuditLog:
    log_id: str
    actor: str
    role: Role
    action: str
    reason_code: str
    details: str
    masked_subscriber_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class BillingRecord:
    record_id: str
    subscriber_id: str
    plan_id: str
    amount: Decimal
    description: str
    days_used: int = 0
    cycle_days: int = 30
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class StateTransitionRecord:
    transition_id: str
    subscriber_id: str
    from_state: SubscriberState
    to_state: SubscriberState
    actor: str = "SYSTEM"
    role: Role = Role.CSR
    reason: str = ""
    trigger: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class PortOutRecord:
    request_id: str
    subscriber_id: str
    recipient_operator: str
    status: str
    requested_at: datetime
    expires_at: datetime
    resolved_at: Optional[datetime] = None

@dataclass(frozen=True)
class RejectionRecord:
    rejection_id: str
    subscriber_id: str
    stage: str
    rule: str
    reason_code: str
    details: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class Subscriber:
    def __init__(
        self,
        subscriber_id: str,
        preferred_plan_type: PlanType,
        mobile_number_hash: Optional[str] = None,
        identity_proof_hash: Optional[str] = None,
        masked_mobile: Optional[str] = None,
        masked_identity_ref: Optional[str] = None,
        mobile_number: Optional[str] = None,
        identity_proof_ref: Optional[str] = None,
        state: SubscriberState = SubscriberState.PENDING_KYC,
        current_plan_id: Optional[str] = None,
        plan_activated_at: Optional[datetime] = None,
        initial_activated_at: Optional[datetime] = None,
        pending_plan_id: Optional[str] = None,
        pending_plan_effective_from: Optional[datetime] = None,
        previous_state: Optional[SubscriberState] = None,
        suspension_reason: Optional[str] = None,
        port_out_requested_at: Optional[datetime] = None,
        is_consumption_active: bool = False,
        created_at: Optional[datetime] = None
    ):
        self.subscriber_id = subscriber_id
        self.preferred_plan_type = preferred_plan_type
        self._raw_mobile = mobile_number
        self.mobile_number_hash = mobile_number_hash or (hash_pii(mobile_number) if mobile_number else "")
        self.identity_proof_hash = identity_proof_hash or (hash_pii(identity_proof_ref) if identity_proof_ref else "")
        self.masked_mobile = masked_mobile or (mask_mobile(mobile_number) if mobile_number else "")
        self.masked_identity_ref = masked_identity_ref or "[REDACTED]"
        self.state = state
        self.current_plan_id = current_plan_id
        self.plan_activated_at = plan_activated_at
        self.initial_activated_at = initial_activated_at
        self.pending_plan_id = pending_plan_id
        self.pending_plan_effective_from = pending_plan_effective_from
        self.previous_state = previous_state
        self.suspension_reason = suspension_reason
        self.port_out_requested_at = port_out_requested_at
        self.is_consumption_active = is_consumption_active
        self.created_at = created_at or datetime.now(timezone.utc)

    @property
    def mobile_number(self) -> str:
        """Returns mobile number if available in memory, otherwise masked."""
        return self._raw_mobile if self._raw_mobile else self.masked_mobile

    def mask_pii(self) -> Dict[str, Any]:
        """Sanitizes subscriber representation for external consumption (NFR-03, NFR-06)."""
        return {
            "subscriber_id": self.subscriber_id,
            "masked_subscriber_id": mask_subscriber_id(self.subscriber_id),
            "mobile_number": self.masked_mobile,
            "identity_proof_ref": "[REDACTED]",
            "preferred_plan_type": self.preferred_plan_type.value if hasattr(self.preferred_plan_type, "value") else str(self.preferred_plan_type),
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "current_plan_id": self.current_plan_id,
            "pending_plan_id": self.pending_plan_id,
            "pending_plan_effective_from": self.pending_plan_effective_from.isoformat() if self.pending_plan_effective_from else None,
            "plan_activated_at": self.plan_activated_at.isoformat() if self.plan_activated_at else None,
            "port_out_requested_at": self.port_out_requested_at.isoformat() if self.port_out_requested_at else None,
            "is_consumption_active": self.is_consumption_active
        }
