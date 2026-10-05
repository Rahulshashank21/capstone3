from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

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

class DomainException(Exception):
    def __init__(self, message: str, reason_code: str):
        super().__init__(message)
        self.message = message
        self.reason_code = reason_code

class InvalidSubscriberStateException(DomainException):
    pass

class PlanImmutableException(DomainException):
    pass

class ActivationFailedException(DomainException):
    pass

class ProRataCalculationException(DomainException):
    pass

@dataclass(frozen=True)
class PlanVersion:
    plan_id: str
    version: int
    name: str
    plan_type: PlanType
    monthly_rent: Decimal
    validity_days: int
    data_gb: int
    min_tenure_days: int = 0
    is_published: bool = False

    def validate_immutability(self) -> None:
        if self.is_published:
            raise PlanImmutableException("Cannot modify a published plan version", "ERR_PLAN_IMMUTABLE")

@dataclass
class Subscriber:
    subscriber_id: str
    mobile_number: str
    identity_proof_ref: str
    preferred_plan_type: PlanType
    state: SubscriberState = SubscriberState.PENDING_KYC
    current_plan_id: Optional[str] = None
    plan_activated_at: Optional[datetime] = None
    port_out_requested_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def mask_pii(self) -> Dict[str, Any]:
        masked_mobile = "XXXXXX" + self.mobile_number[-4:] if len(self.mobile_number) >= 4 else "XXXX"
        return {
            "subscriber_id": self.subscriber_id,
            "mobile_number": masked_mobile,
            "identity_proof_ref": "[REDACTED]",
            "preferred_plan_type": self.preferred_plan_type,
            "state": self.state,
            "current_plan_id": self.current_plan_id
        }

@dataclass
class AuditLog:
    log_id: str
    actor: str
    role: Role
    action: str
    reason_code: str
    details: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
