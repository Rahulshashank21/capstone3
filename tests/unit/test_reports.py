import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from src.domain.models import SubscriberState, PlanType
from src.services.subscription_service import SubscriptionService
from src.services.reporting_service import ReportingService

@pytest.fixture
def populated_system():
    srv = SubscriptionService()
    srv.create_plan("PLAN-PRE-1", "Prepaid 15", PlanType.PREPAID, Decimal("15.00"), 28, 5, is_published=True)
    srv.create_plan("PLAN-POST-1", "Postpaid 50", PlanType.POSTPAID, Decimal("50.00"), 30, 25, is_published=True)
    srv.create_plan("PLAN-POST-2", "Postpaid 100", PlanType.POSTPAID, Decimal("100.00"), 30, 60, is_published=True)

    # 1. Active Prepaid
    s1 = srv.register_subscriber("9876543250", "ID-1", PlanType.PREPAID)
    srv.activate_subscriber(s1.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-PRE-1")

    # 2. Active Postpaid 50
    s2 = srv.register_subscriber("9876543251", "ID-2", PlanType.POSTPAID)
    srv.activate_subscriber(s2.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-1")

    # 3. Active Postpaid 100
    s3 = srv.register_subscriber("9876543252", "ID-3", PlanType.POSTPAID)
    srv.activate_subscriber(s3.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-2")

    # 4. Pending KYC
    srv.register_subscriber("9876543253", "ID-4", PlanType.PREPAID)

    # 5. Ported Out
    s5 = srv.register_subscriber("9876543254", "ID-5", PlanType.POSTPAID)
    srv.activate_subscriber(s5.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-1")
    srv.initiate_port_out(s5.subscriber_id)
    s5.port_out_requested_at = datetime.now(timezone.utc) - timedelta(days=8)
    srv.subscriber_repo.save(s5)
    srv.finalize_port_out(s5.subscriber_id)

    # 6. Suspended
    s6 = srv.register_subscriber("9876543255", "ID-6", PlanType.POSTPAID)
    srv.activate_subscriber(s6.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-1")
    srv.suspend_subscriber(s6.subscriber_id)

    reporting = ReportingService(
        subscriber_repo=srv.subscriber_repo,
        plan_repo=srv.plan_repo,
        audit_repo=srv.audit_repo,
        billing_repo=srv.billing_repo
    )
    return reporting

def test_ac_10_activation_funnel_metrics(populated_system):
    """AC-10: Activation funnel tracks registered, active count, and conversion rate."""
    funnel = populated_system.get_activation_funnel()
    assert funnel["total_registered"] == 6
    assert funnel["total_active"] == 3
    # 3 active / 6 registered = 50.00%
    assert funnel["conversion_rate_percentage"] == Decimal("50.00")
    assert funnel["state_breakdown"]["PENDING_KYC"] == 1
    assert funnel["state_breakdown"]["ACTIVE"] == 3
    assert funnel["state_breakdown"]["SUSPENDED"] == 1
    assert funnel["state_breakdown"]["PORTED_OUT"] == 1

def test_ac_10_churn_rate_metrics(populated_system):
    """AC-10: Churn rate measures terminated and ported-out subscribers."""
    churn = populated_system.get_churn_metrics()
    assert churn["total_subscribers"] == 6
    assert churn["churned_count"] == 1
    # 1 churned / 6 total = 16.67%
    assert churn["monthly_churn_rate_percentage"] == Decimal("16.67")
    assert churn["churn_by_category"]["PORTED_OUT"] == 1

def test_ac_10_plan_mix_distribution(populated_system):
    """AC-10: Plan mix computes prepaid vs postpaid proportions for active subscribers."""
    plan_mix = populated_system.get_plan_mix()
    assert plan_mix["total_active_subscribers"] == 3
    assert plan_mix["prepaid_count"] == 1
    assert plan_mix["postpaid_count"] == 2
    # 1 / 3 = 33.33%, 2 / 3 = 66.67%
    assert plan_mix["prepaid_percentage"] == Decimal("33.33")
    assert plan_mix["postpaid_percentage"] == Decimal("66.67")

def test_ac_10_arpu_calculation(populated_system):
    """AC-10: ARPU aggregates active recurring revenue normalized per active subscriber."""
    arpu_report = populated_system.get_arpu()
    assert arpu_report["total_active_subscribers"] == 3
    # Active rents: 15.00 (prepaid) + 50.00 (postpaid) + 100.00 (postpaid) = 165.00
    assert arpu_report["monthly_recurring_revenue"] == Decimal("165.00")
    # 165.00 / 3 = 55.00
    assert arpu_report["arpu"] == Decimal("55.00")
