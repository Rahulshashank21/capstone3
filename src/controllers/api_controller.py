import uuid
import json
import logging
from datetime import datetime, timezone
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
            # Enforce caller authorization: only DEALER, CSR, or ADMIN can activate (NFR-04)
            if caller_role not in [Role.DEALER, Role.CSR, Role.ADMIN]:
                raise UnauthorizedException(
                    f"Role '{caller_role.value if hasattr(caller_role, 'value') else caller_role}' is not authorized to activate subscriptions. Must be DEALER, CSR, or ADMIN.",
                    "ERR_UNAUTHORIZED"
                )

            dealer_code = payload.get("dealer_code") or (caller_id if caller_role == Role.DEALER else "DEALER_001")
            sub = self.service.activate_subscriber(
                subscriber_id=payload["subscriber_id"],
                kyc_status=payload["kyc_status"],
                dealer_code=dealer_code,
                mnp_status=payload.get("mnp_status", "COMPLETED"),
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
            rejection_id = payload.get("rejection_id")
            CSROverridePolicy.validate_override_request(caller_role, payload.get("reason_code", ""), rejection_id)
            sub = self.service.csr_override_activation(
                subscriber_id=payload["subscriber_id"],
                initial_plan_id=payload["initial_plan_id"],
                actor_id=caller_id,
                reason_code=payload["reason_code"],
                rejection_id=rejection_id
            )
            self._format_log(corr_id, "CSR_OVERRIDE", caller_id, sub.mask_pii()["masked_subscriber_id"], "CSR override activation succeeded")
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_reports(self, caller_role: Role, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        if caller_role not in [Role.ADMIN, Role.CSR]:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": "ERR_UNAUTHORIZED", "message": "Only Admins and CSRs can view operational reports"}

        self._format_log(corr_id, "REPORTS_ACCESSED", caller_role.value if hasattr(caller_role, "value") else str(caller_role), "N/A", "Operational summary reports accessed")
        summary = self.reporting_service.get_dashboard_summary()
        # Convert Decimal objects to strings for clean JSON serialization
        summary["activation_funnel"]["conversion_rate_percentage"] = str(summary["activation_funnel"]["conversion_rate_percentage"])
        summary["churn_metrics"]["monthly_churn_rate_percentage"] = str(summary["churn_metrics"]["monthly_churn_rate_percentage"])
        summary["plan_mix"]["prepaid_percentage"] = str(summary["plan_mix"]["prepaid_percentage"])
        summary["plan_mix"]["postpaid_percentage"] = str(summary["plan_mix"]["postpaid_percentage"])
        summary["arpu"]["monthly_recurring_revenue"] = str(summary["arpu"]["monthly_recurring_revenue"])
        summary["arpu"]["arpu"] = str(summary["arpu"]["arpu"])

        return {"status": "SUCCESS", "correlation_id": corr_id, "data": summary}

    def handle_terminate(self, payload: Dict[str, Any], caller_role: Role, caller_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            if caller_role not in [Role.CSR, Role.ADMIN]:
                raise UnauthorizedException("Only CSR or ADMIN roles can terminate subscriptions", "ERR_UNAUTHORIZED")
            sub_id = payload["subscriber_id"]
            reason = payload.get("reason", "ACCOUNT_CLOSED")
            sub = self.service.terminate_subscriber(sub_id, reason=reason, actor=caller_id, role=caller_role)
            self._format_log(corr_id, "TERMINATE", caller_id, sub.mask_pii()["masked_subscriber_id"], f"Subscription terminated: {reason}")
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_finalize_port_out(self, payload: Dict[str, Any], caller_role: Role, caller_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            if caller_role not in [Role.CSR, Role.ADMIN]:
                raise UnauthorizedException("Only CSR or ADMIN roles can finalize port-out", "ERR_UNAUTHORIZED")
            sub_id = payload["subscriber_id"]
            force_override = bool(payload.get("force_override", False))
            override_reason = payload.get("override_reason")
            sub = self.service.finalize_port_out(
                subscriber_id=sub_id,
                force_override=force_override,
                enforce_cooling_period=True,
                caller_role=caller_role,
                override_reason=override_reason,
                actor=caller_id
            )
            self._format_log(corr_id, "PORT_OUT_FINALIZED", caller_id, sub.mask_pii()["masked_subscriber_id"], "Port-out finalized")
            return {"status": "SUCCESS", "correlation_id": corr_id, "data": sub.mask_pii()}
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}

    def handle_pro_rata_preview(
        self,
        payload: Dict[str, Any],
        caller_role: Optional[Role] = None,
        caller_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        corr_id = correlation_id or f"REQ-{uuid.uuid4().hex[:8]}"
        try:
            sub_id = payload["subscriber_id"]
            if caller_role is not None and caller_id is not None:
                self._verify_subscriber_access(sub_id, caller_role, caller_id)

            new_plan_id = payload["new_plan_id"]
            days_used = payload.get("days_used")
            cycle_days = payload.get("cycle_days", 30)
            sub = self.service.get_subscriber(sub_id)
            if not sub.current_plan_id:
                raise DomainException("Subscriber has no active plan to preview migration from", "ERR_NO_ACTIVE_PLAN", http_status=422)

            current_plan = self.service.plan_repo.find_latest(sub.current_plan_id)
            new_plan = self.service.plan_repo.find_latest_published(new_plan_id)
            if not new_plan:
                draft = self.service.plan_repo.find_latest(new_plan_id)
                if draft:
                    raise DomainException(f"Cannot preview migration to draft or unpublished plan '{new_plan_id}'", "ERR_PLAN_NOT_PUBLISHED", http_status=422)
                raise DomainException(f"Target plan '{new_plan_id}' not found", "ERR_PLAN_NOT_FOUND", http_status=404)

            if not current_plan:
                raise DomainException("Current plan configuration not found", "ERR_PLAN_NOT_FOUND", http_status=404)

            from src.domain.plan_change_policy import PlanChangePolicy
            now = datetime.now(timezone.utc)
            tenure_anchor = sub.initial_activated_at or sub.plan_activated_at or now
            served_days = int((now - tenure_anchor).total_seconds() // 86400)
            tenure_satisfied = served_days >= current_plan.min_tenure_days if current_plan.min_tenure_days > 0 else True

            immediate_mode = days_used is not None or current_plan.plan_type == PlanType.PREPAID
            preview = PlanChangePolicy.evaluate_migration(
                current_plan=current_plan,
                new_plan=new_plan,
                plan_activated_at=sub.plan_activated_at,
                initial_activated_at=sub.initial_activated_at,
                days_used=days_used,
                cycle_days=cycle_days,
                immediate_pro_rata=immediate_mode,
                bypass_tenure=True
            )
            return {
                "status": "SUCCESS",
                "correlation_id": corr_id,
                "data": {
                    "subscriber_id": sub_id,
                    "masked_subscriber_id": sub.mask_pii()["masked_subscriber_id"],
                    "current_plan_id": current_plan.plan_id,
                    "target_plan_id": new_plan.plan_id,
                    "is_upgrade": preview["is_upgrade"],
                    "tenure_satisfied": tenure_satisfied,
                    "min_tenure_days": current_plan.min_tenure_days,
                    "effective_mode": preview["effective_mode"],
                    "charge": str(preview["charge"]),
                    "pro_rata_charge": str(preview["charge"]),
                    "itemized": {k: str(v) for k, v in preview["itemized"].items()} if preview.get("itemized") else None
                }
            }
        except DomainException as e:
            return {"status": "ERROR", "correlation_id": corr_id, "reason_code": e.reason_code, "message": e.message}
