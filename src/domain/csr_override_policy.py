from typing import Set, Optional
from src.domain.models import Role, UnauthorizedException, DomainException

class CSROverridePolicy:
    """Enforces role-based permissions, rejection-record tracking, and mandatory reason codes for operational overrides."""

    AUTHORIZED_ROLES: Set[Role] = {Role.CSR, Role.ADMIN}

    ALLOWED_REASON_CODES: Set[str] = {
        "OVERRIDE_KYC_MANUAL",
        "OVERRIDE_DEALER_SPECIAL",
        "OVERRIDE_TENURE_WAIVER",
        "OVERRIDE_MNP_CLEARANCE",
        "OVERRIDE_BILLING_DISPUTE"
    }

    @classmethod
    def validate_override_request(
        cls,
        actor_role: Role,
        reason_code: str,
        rejection_id: Optional[str] = None
    ) -> None:
        if actor_role not in cls.AUTHORIZED_ROLES:
            raise UnauthorizedException(
                f"Role '{actor_role.value if hasattr(actor_role, 'value') else actor_role}' is not authorized to perform operational overrides",
                "ERR_UNAUTHORIZED"
            )
        if not reason_code or reason_code not in cls.ALLOWED_REASON_CODES:
            raise DomainException(
                f"Invalid or missing override reason code: '{reason_code}'. Allowed: {sorted(list(cls.ALLOWED_REASON_CODES))}",
                "ERR_INVALID_REASON_CODE",
                http_status=422
            )
