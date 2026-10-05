from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List
from src.domain.models import SubscriberState, PlanType
from src.repositories.subscriber_repository import SubscriberRepository
from src.repositories.plan_repository import PlanRepository
from src.repositories.audit_repository import AuditRepository
from src.repositories.billing_repository import BillingRepository

class ReportingService:
    """Consolidates operational data into actionable telecom business intelligence (AC-10)."""

    def __init__(
        self,
        subscriber_repo: SubscriberRepository,
        plan_repo: PlanRepository,
        audit_repo: AuditRepository,
        billing_repo: BillingRepository
    ):
        self.subscriber_repo = subscriber_repo
        self.plan_repo = plan_repo
        self.audit_repo = audit_repo
        self.billing_repo = billing_repo

    def get_activation_funnel(self) -> Dict[str, Any]:
        """Calculates conversion from self-registration to active subscription."""
        all_subs = self.subscriber_repo.list_all()
        total_registered = len(all_subs)
        total_active = sum(1 for s in all_subs if s.state == SubscriberState.ACTIVE)
        
        conversion_rate = Decimal("0.00")
        if total_registered > 0:
            rate = (Decimal(str(total_active)) / Decimal(str(total_registered))) * Decimal("100.00")
            conversion_rate = rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # State breakdown
        breakdown = {}
        for state in SubscriberState:
            breakdown[state.value] = sum(1 for s in all_subs if s.state == state)

        return {
            "total_registered": total_registered,
            "total_active": total_active,
            "conversion_rate_percentage": conversion_rate,
            "state_breakdown": breakdown
        }

    def get_churn_metrics(self) -> Dict[str, Any]:
        """Aggregates churn figures (terminated and ported-out subscribers)."""
        all_subs = self.subscriber_repo.list_all()
        total_registered = len(all_subs)
        
        churned_subs = [s for s in all_subs if s.state in [SubscriberState.TERMINATED, SubscriberState.PORTED_OUT]]
        churned_count = len(churned_subs)

        churn_rate = Decimal("0.00")
        if total_registered > 0:
            rate = (Decimal(str(churned_count)) / Decimal(str(total_registered))) * Decimal("100.00")
            churn_rate = rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Breakdown by churn category
        churn_reasons: Dict[str, int] = {}
        for s in churned_subs:
            key = s.state.value
            churn_reasons[key] = churn_reasons.get(key, 0) + 1

        return {
            "total_subscribers": total_registered,
            "churned_count": churned_count,
            "monthly_churn_rate_percentage": churn_rate,
            "churn_by_category": churn_reasons
        }

    def get_plan_mix(self) -> Dict[str, Any]:
        """Evaluates active subscriber distribution across prepaid and postpaid offerings."""
        active_subs = [s for s in self.subscriber_repo.list_all() if s.state == SubscriberState.ACTIVE]
        total_active = len(active_subs)

        prepaid_count = 0
        postpaid_count = 0
        plan_breakdown: Dict[str, int] = {}

        for sub in active_subs:
            plan = self.plan_repo.find_latest(sub.current_plan_id) if sub.current_plan_id else None
            plan_name = plan.name if plan else (sub.current_plan_id or "UNASSIGNED")
            plan_breakdown[plan_name] = plan_breakdown.get(plan_name, 0) + 1

            if plan and plan.plan_type == PlanType.PREPAID:
                prepaid_count += 1
            elif plan and plan.plan_type == PlanType.POSTPAID:
                postpaid_count += 1

        prepaid_ratio = Decimal("0.00")
        postpaid_ratio = Decimal("0.00")
        if total_active > 0:
            prepaid_ratio = ((Decimal(str(prepaid_count)) / Decimal(str(total_active))) * Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            postpaid_ratio = ((Decimal(str(postpaid_count)) / Decimal(str(total_active))) * Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "total_active_subscribers": total_active,
            "prepaid_count": prepaid_count,
            "postpaid_count": postpaid_count,
            "prepaid_percentage": prepaid_ratio,
            "postpaid_percentage": postpaid_ratio,
            "plan_distribution": plan_breakdown
        }

    def get_arpu(self) -> Dict[str, Any]:
        """Calculates Average Revenue Per User in Decimal currency."""
        active_subs = [s for s in self.subscriber_repo.list_all() if s.state == SubscriberState.ACTIVE]
        total_active = len(active_subs)

        total_recurring_revenue = Decimal("0.00")
        for sub in active_subs:
            if sub.current_plan_id:
                plan = self.plan_repo.find_latest(sub.current_plan_id)
                if plan:
                    total_recurring_revenue += plan.monthly_rent

        arpu = Decimal("0.00")
        if total_active > 0:
            arpu = (total_recurring_revenue / Decimal(str(total_active))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "total_active_subscribers": total_active,
            "monthly_recurring_revenue": total_recurring_revenue.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "arpu": arpu
        }

    def get_dashboard_summary(self) -> Dict[str, Any]:
        return {
            "activation_funnel": self.get_activation_funnel(),
            "churn_metrics": self.get_churn_metrics(),
            "plan_mix": self.get_plan_mix(),
            "arpu": self.get_arpu()
        }
