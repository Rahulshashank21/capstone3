import uuid
import json
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List

from src.domain.models import Role, PlanType, DomainException, UnauthorizedException
from src.domain.csr_override_policy import CSROverridePolicy
from src.services.subscription_service import SubscriptionService
from src.services.reporting_service import ReportingService

logger = logging.getLogger("telcolane.api")

class APIController:
    """REST Controller implementing authentication boundaries, structured logging, and response standardization."""

    def __init__(self, service: SubscriptionService, reporting_service: Optional[ReportingService] = None):
        self.service = service
        self.reporting_service = reporting_service or ReportingService(
            service.subscriber_repo, service.plan_repo, service.audit_repo, service.billing_repo
        )

    def _format_log(self, correlation_id: str, action: str, actor: str, masked_sub_id: str, details: str) -> None:
        log_entry = {
            "correlation_id": correlation_id,
            "action": action,
            "actor": actor,
            "subscriber_id": masked_sub_id,
            "details": details
        }
        logger.info(json.dumps(log_entry))

    def _verify_subscriber_access(self, target_subscriber_id: str, caller_role: Role, caller_id: str) -> None:
        """Enforces that SUBSCRIBERS can only access their own records (NFR-04)."""
        if caller_role == Role.SUBSCRIBER and caller_id != target_subscriber_id:
            raise UnauthorizedException(
                "Subscribers may only view and mutate their own subscription record",
                "ERR_FORBIDDEN_CROSS_SUBSCRIBER"
            )

    # --- Endpoints ---

    def handle_register(self, payload: Dict[str, Any], caller_role: Role, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            mobile = payload["mobile_number"]
            id_ref = payload["identity_proof_ref"]
            plan_type = PlanType(payload["preferred_plan_type"])
            sub = self.service.register_subscriber(mobile, id_ref, plan_type)
            
            masked = sub.mask_pii()
            self._format_log(corr_id, "REGISTER", "PUBLIC", masked["subscriber_id"], "Self-registration completed")
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": masked}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}
        except KeyError as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": "ERR_INVALID_PAYLOAD", "message": f"Missing field: {e}"}

    def handle_activate(self, payload: Dict[str, Any], caller_role: Role, caller_id: str = "DEALER_SYSTEM", correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            sub = self.service.activate_subscriber(
                subscriber_id=payload["subscriber_id"],
                kyc_status=payload["kyc_status"],
                dealer_code=payload["dealer_code"],
                mnp_status=payload["mnp_status"],
                initial_plan_id=payload["initial_plan_id"]
            )
            masked = sub.mask_pii()
            self._format_log(corr_id, "ACTIVATE", caller_id, masked["subscriber_id"], "Activation succeeded")
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": masked}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_get_subscriber(self, subscriber_id: str, caller_role: Role, caller_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            self._verify_subscriber_access(subscriber_id, caller_role, caller_id)
            sub = self.service.get_subscriber(subscriber_id)
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_list_plans(self, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        plans = self.service.list_plans(published_only=True)
        plan_data = [
            {
                "plan_id": p.plan_id,
                "version": p.version,
                "name": p.name,
                "plan_type": p.plan_type.value,
                "monthly_rent": str(p.monthly_rent),
                "validity_days": p.validity_days,
                "data_gb": p.data_gb,
                "min_tenure_days": p.min_tenure_days
            }
            for p in plans
        ]
        return {"status": "SUCCESS", "correlation_id": corr_id, "data": plan_data}

    def handle_change_plan(self, payload: Dict[str, Any], caller_role: Role, caller_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            sub_id = payload["subscriber_id"]
            self._verify_subscriber_access(sub_id, caller_role, caller_id)

            res = self.service.change_plan(
                subscriber_id=sub_id,
                new_plan_id=payload["new_plan_id"],
                days_used=payload.get("days_used", 0),
                cycle_days=payload.get("cycle_days", 30)
            )
            res["pro_rata_charge"] = str(res["pro_rata_charge"])
            self._format_log(corr_id, "PLAN_CHANGE", caller_id, sub_id, f"Plan changed to {payload['new_plan_id']}")
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": res}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_suspend(self, payload: Dict[str, Any], caller_role: Role, caller_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            sub_id = payload["subscriber_id"]
            self._verify_subscriber_access(sub_id, caller_role, caller_id)
            sub = self.service.suspend_subscriber(sub_id, reason=payload.get("reason", "REQUESTED_BY_USER"))
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_reactivate(self, payload: Dict[str, Any], caller_role: Role, caller_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            sub_id = payload["subscriber_id"]
            self._verify_subscriber_access(sub_id, caller_role, caller_id)
            sub = self.service.reactivate_subscriber(sub_id)
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_initiate_port_out(self, payload: Dict[str, Any], caller_role: Role, caller_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            sub_id = payload["subscriber_id"]
            self._verify_subscriber_access(sub_id, caller_role, caller_id)
            sub = self.service.initiate_port_out(sub_id, recipient_operator=payload.get("recipient_operator", "UNKNOWN"))
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_cancel_port_out(self, payload: Dict[str, Any], caller_role: Role, caller_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            sub_id = payload["subscriber_id"]
            self._verify_subscriber_access(sub_id, caller_role, caller_id)
            sub = self.service.cancel_port_out(sub_id)
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_csr_override(self, payload: Dict[str, Any], caller_role: Role, caller_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            CSROverridePolicy.validate_override_request(caller_role, payload.get("reason_code", ""))
            sub = self.service.csr_override_activation(
                subscriber_id=payload["subscriber_id"],
                initial_plan_id=payload["initial_plan_id"],
                actor_id=caller_id,
                reason_code=payload["reason_code"]
            )
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_reports(self, caller_role: Role, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        if caller_role not in [Role.ADMIN, Role.CSR]:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": "ERR_UNAUTHORIZED", "message": "Only Admins and CSRs can view operational reports"}

        summary = self.reporting_service.get_dashboard_summary()
        # Convert Decimal objects to strings for clean JSON serialization
        summary["activation_funnel"]["conversion_rate_percentage"] = str(summary["activation_funnel"]["conversion_rate_percentage"])
        summary["churn_metrics"]["monthly_churn_rate_percentage"] = str(summary["churn_metrics"]["monthly_churn_rate_percentage"])
        summary["plan_mix"]["prepaid_percentage"] = str(summary["plan_mix"]["prepaid_percentage"])
        summary["plan_mix"]["postpaid_percentage"] = str(summary["plan_mix"]["postpaid_percentage"])
        summary["arpu"]["monthly_recurring_revenue"] = str(summary["arpu"]["monthly_recurring_revenue"])
        summary["arpu"]["arpu"] = str(summary["arpu"]["arpu"])

        return {"status": "SUCCESS", "correlation_id": corr_id, "data": summary}
