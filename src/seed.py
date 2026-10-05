from decimal import Decimal
from datetime import datetime, timezone, timedelta
from src.domain.models import PlanType, SubscriberState, Role, AuditLog
from src.services.subscription_service import SubscriptionService

def seed_database(service: SubscriptionService) -> None:
    """Pre-populates the database with compliant telecom sample plans, subscribers, and audit trails."""
    if service.plan_repo.count() > 0 or len(service.subscriber_repo.list_all()) > 0:
        return
    # 1. Seed Plan Catalog (AC-03)
    p1 = service.create_plan(
        plan_id="PLAN-PRE-STARTER",
        name="Prepaid Starter 28D",
        plan_type=PlanType.PREPAID,
        monthly_rent=Decimal("19.99"),
        validity_days=28,
        data_gb=15,
        voice_minutes=-1,
        sms_count=100,
        is_published=True
    )
    p2 = service.create_plan(
        plan_id="PLAN-PRE-MAX",
        name="Prepaid Max 84D",
        plan_type=PlanType.PREPAID,
        monthly_rent=Decimal("49.99"),
        validity_days=84,
        data_gb=90,
        voice_minutes=-1,
        sms_count=100,
        is_published=True
    )
    p3 = service.create_plan(
        plan_id="PLAN-POST-SILVER",
        name="Postpaid Silver 5G",
        plan_type=PlanType.POSTPAID,
        monthly_rent=Decimal("39.99"),
        validity_days=30,
        data_gb=50,
        voice_minutes=-1,
        sms_count=-1,
        min_tenure_days=30,
        is_published=True
    )
    p4 = service.create_plan(
        plan_id="PLAN-POST-GOLD",
        name="Postpaid Gold Unlimited",
        plan_type=PlanType.POSTPAID,
        monthly_rent=Decimal("79.99"),
        validity_days=30,
        data_gb=150,
        voice_minutes=-1,
        sms_count=-1,
        min_tenure_days=60,
        is_published=True
    )

    # 2. Seed Sample Subscribers in various lifecycle states
    # Active Postpaid
    s1 = service.register_subscriber("9876543201", "ID-PROOF-KYC-01", PlanType.POSTPAID)
    service.activate_subscriber(s1.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-SILVER")

    # Active Prepaid
    s2 = service.register_subscriber("9876543202", "ID-PROOF-KYC-02", PlanType.PREPAID)
    service.activate_subscriber(s2.subscriber_id, "VERIFIED", "DEALER_002", "APPROVED", "PLAN-PRE-STARTER")

    # Suspended Subscriber
    s3 = service.register_subscriber("9876543203", "ID-PROOF-KYC-03", PlanType.POSTPAID)
    service.activate_subscriber(s3.subscriber_id, "VERIFIED", "OFFICIAL_WEB", "APPROVED", "PLAN-POST-SILVER")
    service.suspend_subscriber(s3.subscriber_id, reason="NON_PAYMENT")

    # Port-Out Requested (Day 2 of 7-day cooling)
    s4 = service.register_subscriber("9876543204", "ID-PROOF-KYC-04", PlanType.POSTPAID)
    service.activate_subscriber(s4.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-POST-GOLD")
    service.initiate_port_out(s4.subscriber_id, recipient_operator="COMPETITOR_TELCO")
    s4.port_out_requested_at = datetime.now(timezone.utc) - timedelta(days=2)
    service.subscriber_repo.save(s4)

    # Pending KYC
    service.register_subscriber("9876543205", "ID-PROOF-KYC-05", PlanType.PREPAID)

    # Ported Out (Terminal)
    s6 = service.register_subscriber("9876543206", "ID-PROOF-KYC-06", PlanType.POSTPAID)
    s6 = service.activate_subscriber(s6.subscriber_id, "VERIFIED", "DEALER_002", "APPROVED", "PLAN-POST-SILVER")
    s6 = service.initiate_port_out(s6.subscriber_id)
    s6.port_out_requested_at = datetime.now(timezone.utc) - timedelta(days=8)
    service.subscriber_repo.save(s6)
    service.finalize_port_out(s6.subscriber_id)

    print(f"[SEED] Successfully seeded {service.plan_repo.count()} plans and {len(service.subscriber_repo.list_all())} subscribers.")

if __name__ == "__main__":
    srv = SubscriptionService()
    seed_database(srv)
