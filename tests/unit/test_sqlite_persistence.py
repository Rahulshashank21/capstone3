import os
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from src.infrastructure.database import (
    Database, SqliteSubscriberRepository, SqlitePlanRepository,
    SqliteAuditRepository, SqliteBillingRepository,
    SqlitePortOutRepository, SqliteRejectionRepository
)
from src.domain.models import (
    Subscriber, SubscriberState, PlanType, PlanVersion,
    AuditLog, BillingRecord, PortOutRecord, RejectionRecord, Role,
    PlanImmutableException, ActivationFailedException
)

@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test_telcolane.db")
    db = Database(db_path)
    return db

def test_sqlite_subscriber_persistence_and_number_uniqueness(temp_db):
    repo = SqliteSubscriberRepository(temp_db)
    sub1 = Subscriber(
        subscriber_id="SUB-SQL-01",
        mobile_number="9876543299",
        preferred_plan_type=PlanType.PREPAID,
        state=SubscriberState.ACTIVE
    )
    repo.save(sub1)

    fetched = repo.find_by_id("SUB-SQL-01")
    assert fetched is not None
    assert fetched.subscriber_id == "SUB-SQL-01"
    assert fetched.state == SubscriberState.ACTIVE

    # Attempting to insert another ACTIVE subscriber with identical mobile number hash fails atomically
    sub2 = Subscriber(
        subscriber_id="SUB-SQL-02",
        mobile_number="9876543299",
        preferred_plan_type=PlanType.POSTPAID,
        state=SubscriberState.ACTIVE
    )
    with pytest.raises(ActivationFailedException) as exc_info:
        repo.save(sub2)
    assert exc_info.value.reason_code == "ERR_DUPLICATE_ACTIVE_NUMBER"

def test_sqlite_plan_immutability(temp_db):
    plan_repo = SqlitePlanRepository(temp_db)
    p = PlanVersion(
        plan_id="PLAN-SQL-01",
        version=1,
        name="Test Plan",
        plan_type=PlanType.POSTPAID,
        monthly_rent=Decimal("49.99"),
        validity_days=30,
        data_gb=20,
        is_published=True
    )
    plan_repo.save(p)

    # Attempt to overwrite published plan must raise PlanImmutableException
    p_modified = PlanVersion(
        plan_id="PLAN-SQL-01",
        version=1,
        name="Modified Plan",
        plan_type=PlanType.POSTPAID,
        monthly_rent=Decimal("29.99"),
        validity_days=30,
        data_gb=20,
        is_published=True
    )
    with pytest.raises(PlanImmutableException):
        plan_repo.save(p_modified)

def test_sqlite_audit_and_billing_append_only(temp_db):
    audit_repo = SqliteAuditRepository(temp_db)
    billing_repo = SqliteBillingRepository(temp_db)

    now = datetime.now(timezone.utc)
    log = AuditLog(
        log_id="AUD-SQL-01",
        actor="ADMIN_TEST",
        role=Role.ADMIN,
        action="TEST_ACTION",
        reason_code="REASON_TEST",
        details="Test audit log persistence",
        masked_subscriber_id="SUB-XXXX1234",
        timestamp=now
    )
    audit_repo.append(log)

    logs = audit_repo.find_by_actor("ADMIN_TEST")
    assert len(logs) == 1
    assert logs[0].action == "TEST_ACTION"

    billing = BillingRecord(
        record_id="BIL-SQL-01",
        subscriber_id="SUB-SQL-01",
        plan_id="PLAN-SQL-01",
        amount=Decimal("49.99"),
        description="Monthly postpaid charge",
        days_used=30,
        cycle_days=30,
        timestamp=now
    )
    billing_repo.append(billing)

    records = billing_repo.list_by_subscriber("SUB-SQL-01")
    assert len(records) == 1
    assert records[0].amount == Decimal("49.99")

def test_sqlite_port_out_repository(temp_db):
    repo = SqlitePortOutRepository(temp_db)
    now = datetime.now(timezone.utc)
    rec = PortOutRecord(
        request_id="POR-SQL-01",
        subscriber_id="SUB-SQL-01",
        recipient_operator="AIRTEL_IND",
        status="COOLING",
        requested_at=now,
        expires_at=now
    )
    repo.append(rec)

    active = repo.find_active_by_subscriber("SUB-SQL-01")
    assert active is not None
    assert active.request_id == "POR-SQL-01"
    assert active.recipient_operator == "AIRTEL_IND"

    repo.mark_cancelled("POR-SQL-01", now)
    assert repo.find_active_by_subscriber("SUB-SQL-01") is None

    # Test finalization status update
    rec2 = PortOutRecord(
        request_id="POR-SQL-02",
        subscriber_id="SUB-SQL-01",
        recipient_operator="JIO_IND",
        status="COOLING",
        requested_at=now,
        expires_at=now
    )
    repo.append(rec2)
    repo.mark_finalized("POR-SQL-02", now)
    assert repo.find_active_by_subscriber("SUB-SQL-01") is None

def test_sqlite_rejection_and_state_transition_repos(temp_db):
    from src.infrastructure.database import SqliteStateTransitionRepository
    from src.domain.models import StateTransitionRecord

    rej_repo = SqliteRejectionRepository(temp_db)
    trans_repo = SqliteStateTransitionRepository(temp_db)
    now = datetime.now(timezone.utc)

    # Rejection repo
    rej = RejectionRecord(
        rejection_id="REJ-01",
        subscriber_id="SUB-REJ-01",
        stage="ACTIVATION",
        rule="KYC_VERIFICATION",
        reason_code="ERR_KYC_FAILED",
        details="Aadhaar photo mismatch",
        timestamp=now
    )
    rej_repo.record(rej)
    by_sub = rej_repo.find_by_subscriber("SUB-REJ-01")
    assert len(by_sub) == 1
    assert rej_repo.find_by_id("REJ-01") is not None

    # State transition repo
    trans = StateTransitionRecord(
        transition_id="TR-01",
        subscriber_id="SUB-REJ-01",
        from_state=SubscriberState.PENDING_KYC,
        to_state=SubscriberState.ACTIVE,
        actor="CSR_99",
        role=Role.CSR,
        reason="Manual approval",
        timestamp=now
    )
    trans_repo.append(trans)
    trans_list = trans_repo.list_by_subscriber("SUB-REJ-01")
    assert len(trans_list) == 1
    assert trans_list[0].to_state == SubscriberState.ACTIVE

def test_sqlite_pagination(temp_db):
    sub_repo = SqliteSubscriberRepository(temp_db)
    audit_repo = SqliteAuditRepository(temp_db)
    billing_repo = SqliteBillingRepository(temp_db)

    for i in range(5):
        sub_repo.save(Subscriber(
            subscriber_id=f"SUB-PAG-{i}",
            mobile_number=f"981100000{i}",
            preferred_plan_type=PlanType.PREPAID,
            state=SubscriberState.PENDING_KYC
        ))
        audit_repo.append(AuditLog(
            log_id=f"AUD-PAG-{i}",
            actor="SYSTEM",
            role=Role.ADMIN,
            action="BATCH_INSERT",
            reason_code="TEST",
            details="Pagination test"
        ))
        billing_repo.append(BillingRecord(
            record_id=f"BIL-PAG-{i}",
            subscriber_id=f"SUB-PAG-{i}",
            plan_id="PLAN-TEST",
            amount=Decimal("10.00"),
            description="Test bill"
        ))

    # Paginate subscribers
    p1 = sub_repo.list_paginated(limit=2, offset=0)
    assert len(p1) == 2
    p2 = sub_repo.list_paginated(limit=2, offset=2)
    assert len(p2) == 2
    assert p1[0].subscriber_id != p2[0].subscriber_id

    # Paginate audit and billing
    assert len(audit_repo.list_paginated(limit=3, offset=0)) == 3
    assert len(billing_repo.list_paginated(limit=3, offset=0)) == 3
    assert sub_repo.count() >= 5
    assert audit_repo.count() >= 5
    assert billing_repo.count() >= 5

def test_sqlite_service_restart_persistence(tmp_path):
    """Verifies complete state recovery across service shutdown and cold reboot."""
    from src.infrastructure.database import create_sqlite_subscription_service

    db_file = str(tmp_path / "restart_test.db")

    # Instance 1: Provision and mutate
    srv1 = create_sqlite_subscription_service(db_file)
    srv1.create_plan("PLAN-RESTART-1", "Restart Plan 1", PlanType.POSTPAID, Decimal("49.99"), 30, 25, is_published=True)
    srv1.create_plan("PLAN-RESTART-2", "Restart Plan 2", PlanType.POSTPAID, Decimal("79.99"), 30, 50, is_published=True)

    sub = srv1.register_subscriber("9899001122", "ID-RESTART-01", PlanType.POSTPAID)
    sub_id = sub.subscriber_id
    srv1.activate_subscriber(sub_id, "VERIFIED", "DEALER_001", "COMPLETED", "PLAN-RESTART-1")
    srv1.change_plan(sub_id, "PLAN-RESTART-2", days_used=10, cycle_days=30, immediate_pro_rata=True)

    # Simulate shutdown by unsetting references
    del srv1

    # Instance 2: Cold reboot against the exact same SQLite database file
    srv2 = create_sqlite_subscription_service(db_file)

    recovered_sub = srv2.get_subscriber(sub_id)
    assert recovered_sub is not None
    assert recovered_sub.subscriber_id == sub_id
    assert recovered_sub.state == SubscriberState.ACTIVE
    assert recovered_sub.current_plan_id == "PLAN-RESTART-2"
    assert recovered_sub.masked_mobile == "XXXXXX1122"
    assert recovered_sub.mobile_number_hash == sub.mobile_number_hash

    # Invariant: Audit logs and billing records intact across reboot
    audit_entries = srv2.audit_repo.list_all()
    assert len(audit_entries) >= 2

    billing_entries = srv2.billing_repo.list_by_subscriber(sub_id)
    assert len(billing_entries) >= 1
    assert billing_entries[0].plan_id == "PLAN-RESTART-2"

