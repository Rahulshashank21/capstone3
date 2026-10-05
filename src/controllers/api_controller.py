from typing import Dict, Any, Optional
from src.domain.models import Role, PlanType, DomainException
from src.services.subscription_service import SubscriptionService

class APIController:
    def __init__(self, service: SubscriptionService):
        self.service = service

    def handle_register(self, payload: Dict[str, Any], caller_role: Role) -> Dict[str, Any]:
        try:
            mobile = payload["mobile_number"]
            id_ref = payload["identity_proof_ref"]
            plan_type = PlanType(payload["preferred_plan_type"])
            sub = self.service.register_subscriber(mobile, id_ref, plan_type)
            return {"status": "SUCCESS", "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "reason_code": e.reason_code, "message": e.message}
        except KeyError as e:
            return {"status": "ERROR", "reason_code": "ERR_INVALID_PAYLOAD", "message": f"Missing required field: {e}"}

    def handle_activate(self, payload: Dict[str, Any], caller_role: Role) -> Dict[str, Any]:
        try:
            sub = self.service.activate_subscriber(
                subscriber_id=payload["subscriber_id"],
                kyc_status=payload["kyc_status"],
                dealer_code=payload["dealer_code"],
                mnp_status=payload["mnp_status"],
                initial_plan_id=payload["initial_plan_id"]
            )
            return {"status": "SUCCESS", "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "reason_code": e.reason_code, "message": e.message}

    def handle_csr_override(self, payload: Dict[str, Any], caller_role: Role, caller_id: str) -> Dict[str, Any]:
        if caller_role not in [Role.CSR, Role.ADMIN]:
            return {"status": "ERROR", "reason_code": "ERR_UNAUTHORIZED", "message": "Role unauthorized for override"}
        try:
            sub = self.service.csr_override_activation(
                subscriber_id=payload["subscriber_id"],
                initial_plan_id=payload["initial_plan_id"],
                actor_id=caller_id,
                reason_code=payload["reason_code"]
            )
            return {"status": "SUCCESS", "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "reason_code": e.reason_code, "message": e.message}
