import sqlite3
import threading
import os
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from src.domain.models import (
    Subscriber, PlanVersion, AuditLog, BillingRecord, StateTransitionRecord,
    PortOutRecord, RejectionRecord, SubscriberState, PlanType, Role,
    PlanImmutableException, ActivationFailedException, hash_pii
)

DEFAULT_DB_PATH = os.environ.get("TELCOLANE_DB_PATH", "telcolane.db")

class Database:
    """Manages SQLite connection pooling and schema migrations (NFR-05)."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._lock = threading.RLock()
        self.run_migrations()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def run_migrations(self) -> None:
        with self._lock:
            conn = self.get_connection()
            try:
                with conn:
                    conn.executescript("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS subscribers (
                        subscriber_id TEXT PRIMARY KEY,
                        mobile_number_hash TEXT NOT NULL,
                        identity_proof_hash TEXT NOT NULL,
                        masked_mobile TEXT NOT NULL,
                        masked_identity_ref TEXT NOT NULL,
                        preferred_plan_type TEXT NOT NULL,
                        state TEXT NOT NULL,
                        current_plan_id TEXT,
                        pending_plan_id TEXT,
                        pending_plan_effective_from TEXT,
                        plan_activated_at TEXT,
                        initial_activated_at TEXT,
                        previous_state TEXT,
                        suspension_reason TEXT,
                        port_out_requested_at TEXT,
                        is_consumption_active INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL
                    );

                    CREATE UNIQUE INDEX IF NOT EXISTS idx_active_mobile 
                        ON subscribers(mobile_number_hash) 
                        WHERE state = 'ACTIVE';

                    CREATE TABLE IF NOT EXISTS plans (
                        plan_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        plan_type TEXT NOT NULL,
                        monthly_rent TEXT NOT NULL,
                        validity_days INTEGER NOT NULL,
                        data_gb INTEGER NOT NULL,
                        voice_minutes INTEGER NOT NULL DEFAULT -1,
                        sms_count INTEGER NOT NULL DEFAULT -1,
                        min_tenure_days INTEGER NOT NULL DEFAULT 0,
                        is_published INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (plan_id, version)
                    );

                    CREATE TABLE IF NOT EXISTS audit_logs (
                        log_id TEXT PRIMARY KEY,
                        actor TEXT NOT NULL,
                        role TEXT NOT NULL,
                        action TEXT NOT NULL,
                        reason_code TEXT NOT NULL,
                        details TEXT NOT NULL,
                        masked_subscriber_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS billing_records (
                        record_id TEXT PRIMARY KEY,
                        subscriber_id TEXT NOT NULL,
                        plan_id TEXT NOT NULL,
                        amount TEXT NOT NULL,
                        description TEXT NOT NULL,
                        days_used INTEGER NOT NULL,
                        cycle_days INTEGER NOT NULL,
                        timestamp TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS state_transitions (
                        transition_id TEXT PRIMARY KEY,
                        subscriber_id TEXT NOT NULL,
                        from_state TEXT NOT NULL,
                        to_state TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        role TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS port_out_requests (
                        request_id TEXT PRIMARY KEY,
                        subscriber_id TEXT NOT NULL,
                        recipient_operator TEXT NOT NULL,
                        status TEXT NOT NULL,
                        requested_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        resolved_at TEXT
                    );

                    CREATE TABLE IF NOT EXISTS rejections (
                        rejection_id TEXT PRIMARY KEY,
                        subscriber_id TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        rule TEXT NOT NULL,
                        reason_code TEXT NOT NULL,
                        details TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    );
                    """)
            finally:
                conn.close()

# --- SQLite Persistent Repositories ---

class SqliteSubscriberRepository:
    def __init__(self, db: Database):
        self.db = db
        self._lock = db._lock

    def _row_to_entity(self, row: sqlite3.Row) -> Subscriber:
        return Subscriber(
            subscriber_id=row["subscriber_id"],
            mobile_number_hash=row["mobile_number_hash"],
            identity_proof_hash=row["identity_proof_hash"],
            masked_mobile=row["masked_mobile"],
            masked_identity_ref=row["masked_identity_ref"],
            preferred_plan_type=PlanType(row["preferred_plan_type"]),
            state=SubscriberState(row["state"]),
            current_plan_id=row["current_plan_id"],
            pending_plan_id=row["pending_plan_id"],
            pending_plan_effective_from=datetime.fromisoformat(row["pending_plan_effective_from"]) if row["pending_plan_effective_from"] else None,
            plan_activated_at=datetime.fromisoformat(row["plan_activated_at"]) if row["plan_activated_at"] else None,
            initial_activated_at=datetime.fromisoformat(row["initial_activated_at"]) if row["initial_activated_at"] else None,
            previous_state=SubscriberState(row["previous_state"]) if row["previous_state"] else None,
            suspension_reason=row["suspension_reason"],
            port_out_requested_at=datetime.fromisoformat(row["port_out_requested_at"]) if row["port_out_requested_at"] else None,
            is_consumption_active=bool(row["is_consumption_active"]),
            created_at=datetime.fromisoformat(row["created_at"])
        )

    def save(self, subscriber: Subscriber) -> Subscriber:
        with self._lock:
            conn = self.db.get_connection()
            try:
                with conn:
                    # Enforce atomic number exclusivity if transitioning to ACTIVE (NFR-08)
                    if subscriber.state == SubscriberState.ACTIVE:
                        cur = conn.execute(
                            "SELECT subscriber_id FROM subscribers WHERE mobile_number_hash = ? AND state = 'ACTIVE' AND subscriber_id != ?",
                            (subscriber.mobile_number_hash, subscriber.subscriber_id)
                        )
                        if cur.fetchone():
                            raise ActivationFailedException(
                                "Mobile number already holds an ACTIVE subscription on the network",
                                "ERR_DUPLICATE_ACTIVE_NUMBER"
                            )

                    conn.execute("""
                    INSERT INTO subscribers (
                        subscriber_id, mobile_number_hash, identity_proof_hash,
                        masked_mobile, masked_identity_ref, preferred_plan_type,
                        state, current_plan_id, pending_plan_id, pending_plan_effective_from,
                        plan_activated_at, initial_activated_at, previous_state, suspension_reason,
                        port_out_requested_at, is_consumption_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(subscriber_id) DO UPDATE SET
                        mobile_number_hash = excluded.mobile_number_hash,
                        identity_proof_hash = excluded.identity_proof_hash,
                        masked_mobile = excluded.masked_mobile,
                        masked_identity_ref = excluded.masked_identity_ref,
                        preferred_plan_type = excluded.preferred_plan_type,
                        state = excluded.state,
                        current_plan_id = excluded.current_plan_id,
                        pending_plan_id = excluded.pending_plan_id,
                        pending_plan_effective_from = excluded.pending_plan_effective_from,
                        plan_activated_at = excluded.plan_activated_at,
                        initial_activated_at = excluded.initial_activated_at,
                        previous_state = excluded.previous_state,
                        suspension_reason = excluded.suspension_reason,
                        port_out_requested_at = excluded.port_out_requested_at,
                        is_consumption_active = excluded.is_consumption_active;
                    """, (
                        subscriber.subscriber_id,
                        subscriber.mobile_number_hash,
                        subscriber.identity_proof_hash,
                        subscriber.masked_mobile,
                        subscriber.masked_identity_ref,
                        subscriber.preferred_plan_type.value,
                        subscriber.state.value,
                        subscriber.current_plan_id,
                        subscriber.pending_plan_id,
                        subscriber.pending_plan_effective_from.isoformat() if subscriber.pending_plan_effective_from else None,
                        subscriber.plan_activated_at.isoformat() if subscriber.plan_activated_at else None,
                        subscriber.initial_activated_at.isoformat() if subscriber.initial_activated_at else None,
                        subscriber.previous_state.value if subscriber.previous_state else None,
                        subscriber.suspension_reason,
                        subscriber.port_out_requested_at.isoformat() if subscriber.port_out_requested_at else None,
                        1 if subscriber.is_consumption_active else 0,
                        subscriber.created_at.isoformat()
                    ))
                return subscriber
            finally:
                conn.close()

    def find_by_id(self, subscriber_id: str) -> Optional[Subscriber]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM subscribers WHERE subscriber_id = ?", (subscriber_id,))
                row = cur.fetchone()
                return self._row_to_entity(row) if row else None
            finally:
                conn.close()

    def find_by_mobile_hash(self, mobile_number_hash: str) -> List[Subscriber]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM subscribers WHERE mobile_number_hash = ?", (mobile_number_hash,))
                return [self._row_to_entity(r) for r in cur.fetchall()]
            finally:
                conn.close()

    def find_by_mobile(self, mobile_number: str) -> List[Subscriber]:
        return self.find_by_mobile_hash(hash_pii(mobile_number))

    def list_all(self, limit: int = 500, offset: int = 0) -> List[Subscriber]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM subscribers ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
                return [self._row_to_entity(r) for r in cur.fetchall()]
            finally:
                conn.close()

    list_paginated = list_all

    def get_active_number_hashes(self) -> Set[str]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT mobile_number_hash FROM subscribers WHERE state = 'ACTIVE'")
                return {r[0] for r in cur.fetchall()}
            finally:
                conn.close()

    def get_active_numbers(self) -> Set[str]:
        return self.get_active_number_hashes()

    def count_by_state(self, state: SubscriberState) -> int:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT COUNT(*) FROM subscribers WHERE state = ?", (state.value,))
                row = cur.fetchone()
                return row[0] if row else 0
            finally:
                conn.close()

    def count(self) -> int:
        with self._lock:
            conn = self.db.get_connection()
            try:
                return conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
            finally:
                conn.close()

class SqlitePlanRepository:
    def __init__(self, db: Database):
        self.db = db
        self._lock = db._lock

    def _row_to_plan(self, row: sqlite3.Row) -> PlanVersion:
        return PlanVersion(
            plan_id=row["plan_id"],
            version=row["version"],
            name=row["name"],
            plan_type=PlanType(row["plan_type"]),
            monthly_rent=Decimal(row["monthly_rent"]),
            validity_days=row["validity_days"],
            data_gb=row["data_gb"],
            voice_minutes=row["voice_minutes"],
            sms_count=row["sms_count"],
            min_tenure_days=row["min_tenure_days"],
            is_published=bool(row["is_published"]),
            created_at=datetime.fromisoformat(row["created_at"])
        )

    def save(self, plan: PlanVersion) -> PlanVersion:
        with self._lock:
            conn = self.db.get_connection()
            try:
                with conn:
                    # Enforce published immutability (NFR-02)
                    cur = conn.execute(
                        "SELECT is_published FROM plans WHERE plan_id = ? AND version = ?",
                        (plan.plan_id, plan.version)
                    )
                    existing = cur.fetchone()
                    if existing and existing["is_published"]:
                        raise PlanImmutableException(
                            f"Cannot modify published plan version '{plan.plan_id}:v{plan.version}'",
                            "ERR_PLAN_IMMUTABLE"
                        )

                    conn.execute("""
                    INSERT INTO plans (
                        plan_id, version, name, plan_type, monthly_rent,
                        validity_days, data_gb, voice_minutes, sms_count,
                        min_tenure_days, is_published, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(plan_id, version) DO UPDATE SET
                        name = excluded.name,
                        monthly_rent = excluded.monthly_rent,
                        validity_days = excluded.validity_days,
                        data_gb = excluded.data_gb,
                        voice_minutes = excluded.voice_minutes,
                        sms_count = excluded.sms_count,
                        min_tenure_days = excluded.min_tenure_days,
                        is_published = excluded.is_published;
                    """, (
                        plan.plan_id, plan.version, plan.name, plan.plan_type.value,
                        str(plan.monthly_rent), plan.validity_days, plan.data_gb,
                        plan.voice_minutes, plan.sms_count, plan.min_tenure_days,
                        1 if plan.is_published else 0, plan.created_at.isoformat()
                    ))
                return plan
            finally:
                conn.close()

    def find_latest(self, plan_id: str) -> Optional[PlanVersion]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM plans WHERE plan_id = ? ORDER BY version DESC LIMIT 1", (plan_id,))
                row = cur.fetchone()
                return self._row_to_plan(row) if row else None
            finally:
                conn.close()

    def find_latest_published(self, plan_id: str) -> Optional[PlanVersion]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute(
                    "SELECT * FROM plans WHERE plan_id = ? AND is_published = 1 ORDER BY version DESC LIMIT 1",
                    (plan_id,)
                )
                row = cur.fetchone()
                return self._row_to_plan(row) if row else None
            finally:
                conn.close()

    def find_by_version(self, plan_id: str, version: int) -> Optional[PlanVersion]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM plans WHERE plan_id = ? AND version = ?", (plan_id, version))
                row = cur.fetchone()
                return self._row_to_plan(row) if row else None
            finally:
                conn.close()

    def list_published(self) -> List[PlanVersion]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("""
                SELECT p.* FROM plans p
                INNER JOIN (
                    SELECT plan_id, MAX(version) as max_v FROM plans WHERE is_published = 1 GROUP BY plan_id
                ) m ON p.plan_id = m.plan_id AND p.version = m.max_v
                ORDER BY p.plan_id ASC
                """)
                return [self._row_to_plan(r) for r in cur.fetchall()]
            finally:
                conn.close()

    def list_all_latest(self) -> List[PlanVersion]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("""
                SELECT p.* FROM plans p
                INNER JOIN (
                    SELECT plan_id, MAX(version) as max_v FROM plans GROUP BY plan_id
                ) m ON p.plan_id = m.plan_id AND p.version = m.max_v
                ORDER BY p.plan_id ASC
                """)
                return [self._row_to_plan(r) for r in cur.fetchall()]
            finally:
                conn.close()

    def count(self) -> int:
        with self._lock:
            conn = self.db.get_connection()
            try:
                return conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
            finally:
                conn.close()

class SqliteAuditRepository:
    def __init__(self, db: Database):
        self.db = db
        self._lock = db._lock

    def append(self, log: AuditLog) -> AuditLog:
        with self._lock:
            conn = self.db.get_connection()
            try:
                with conn:
                    conn.execute("""
                    INSERT INTO audit_logs (log_id, actor, role, action, reason_code, details, masked_subscriber_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        log.log_id, log.actor, log.role.value, log.action,
                        log.reason_code, log.details, log.masked_subscriber_id, log.timestamp.isoformat()
                    ))
                return log
            finally:
                conn.close()

    def list_all(self, limit: int = 200, offset: int = 0) -> List[AuditLog]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
                return [
                    AuditLog(
                        log_id=r["log_id"],
                        actor=r["actor"],
                        role=Role(r["role"]),
                        action=r["action"],
                        reason_code=r["reason_code"],
                        details=r["details"],
                        masked_subscriber_id=r["masked_subscriber_id"],
                        timestamp=datetime.fromisoformat(r["timestamp"])
                    )
                    for r in cur.fetchall()
                ]
            finally:
                conn.close()

    def find_by_actor(self, actor: str) -> List[AuditLog]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM audit_logs WHERE actor = ? ORDER BY timestamp DESC", (actor,))
                return [
                    AuditLog(
                        log_id=r["log_id"],
                        actor=r["actor"],
                        role=Role(r["role"]),
                        action=r["action"],
                        reason_code=r["reason_code"],
                        details=r["details"],
                        masked_subscriber_id=r["masked_subscriber_id"],
                        timestamp=datetime.fromisoformat(r["timestamp"])
                    )
                    for r in cur.fetchall()
                ]
            finally:
                conn.close()

    def find_by_subscriber(self, masked_subscriber_id: str) -> List[AuditLog]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM audit_logs WHERE masked_subscriber_id = ? ORDER BY timestamp DESC", (masked_subscriber_id,))
                return [
                    AuditLog(
                        log_id=r["log_id"],
                        actor=r["actor"],
                        role=Role(r["role"]),
                        action=r["action"],
                        reason_code=r["reason_code"],
                        details=r["details"],
                        masked_subscriber_id=r["masked_subscriber_id"],
                        timestamp=datetime.fromisoformat(r["timestamp"])
                    )
                    for r in cur.fetchall()
                ]
            finally:
                conn.close()

    list_paginated = list_all

    def count(self) -> int:
        with self._lock:
            conn = self.db.get_connection()
            try:
                return conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
            finally:
                conn.close()

class SqliteBillingRepository:
    def __init__(self, db: Database):
        self.db = db
        self._lock = db._lock

    def append(self, record: BillingRecord) -> BillingRecord:
        with self._lock:
            conn = self.db.get_connection()
            try:
                with conn:
                    conn.execute("""
                    INSERT INTO billing_records (record_id, subscriber_id, plan_id, amount, description, days_used, cycle_days, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.record_id, record.subscriber_id, record.plan_id,
                        str(record.amount), record.description, record.days_used,
                        record.cycle_days, record.timestamp.isoformat()
                    ))
                return record
            finally:
                conn.close()

    def list_by_subscriber(self, subscriber_id: str) -> List[BillingRecord]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM billing_records WHERE subscriber_id = ? ORDER BY timestamp DESC", (subscriber_id,))
                return [
                    BillingRecord(
                        record_id=r["record_id"],
                        subscriber_id=r["subscriber_id"],
                        plan_id=r["plan_id"],
                        amount=Decimal(r["amount"]),
                        description=r["description"],
                        days_used=r["days_used"],
                        cycle_days=r["cycle_days"],
                        timestamp=datetime.fromisoformat(r["timestamp"])
                    )
                    for r in cur.fetchall()
                ]
            finally:
                conn.close()

    def list_all(self, limit: int = 200, offset: int = 0) -> List[BillingRecord]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM billing_records ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
                return [
                    BillingRecord(
                        record_id=r["record_id"],
                        subscriber_id=r["subscriber_id"],
                        plan_id=r["plan_id"],
                        amount=Decimal(r["amount"]),
                        description=r["description"],
                        days_used=r["days_used"],
                        cycle_days=r["cycle_days"],
                        timestamp=datetime.fromisoformat(r["timestamp"])
                    )
                    for r in cur.fetchall()
                ]
            finally:
                conn.close()

    list_paginated = list_all

    def count(self) -> int:
        with self._lock:
            conn = self.db.get_connection()
            try:
                return conn.execute("SELECT COUNT(*) FROM billing_records").fetchone()[0]
            finally:
                conn.close()

class SqliteRejectionRepository:
    def __init__(self, db: Database):
        self.db = db
        self._lock = db._lock

    def append(self, rejection: RejectionRecord) -> RejectionRecord:
        with self._lock:
            conn = self.db.get_connection()
            try:
                with conn:
                    conn.execute("""
                    INSERT INTO rejections (rejection_id, subscriber_id, stage, rule, reason_code, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rejection.rejection_id, rejection.subscriber_id, rejection.stage,
                        rejection.rule, rejection.reason_code, rejection.details, rejection.timestamp.isoformat()
                    ))
                return rejection
            finally:
                conn.close()

    def find_by_id(self, rejection_id: str) -> Optional[RejectionRecord]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM rejections WHERE rejection_id = ?", (rejection_id,))
                r = cur.fetchone()
                if not r:
                    return None
                return RejectionRecord(
                    rejection_id=r["rejection_id"],
                    subscriber_id=r["subscriber_id"],
                    stage=r["stage"],
                    rule=r["rule"],
                    reason_code=r["reason_code"],
                    details=r["details"],
                    timestamp=datetime.fromisoformat(r["timestamp"])
                )
            finally:
                conn.close()

    def list_by_subscriber(self, subscriber_id: str) -> List[RejectionRecord]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM rejections WHERE subscriber_id = ? ORDER BY timestamp DESC", (subscriber_id,))
                return [
                    RejectionRecord(
                        rejection_id=r["rejection_id"],
                        subscriber_id=r["subscriber_id"],
                        stage=r["stage"],
                        rule=r["rule"],
                        reason_code=r["reason_code"],
                        details=r["details"],
                        timestamp=datetime.fromisoformat(r["timestamp"])
                    )
                    for r in cur.fetchall()
                ]
            finally:
                conn.close()

    def list_all(self) -> List[RejectionRecord]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM rejections ORDER BY timestamp DESC")
                return [
                    RejectionRecord(
                        rejection_id=r["rejection_id"],
                        subscriber_id=r["subscriber_id"],
                        stage=r["stage"],
                        rule=r["rule"],
                        reason_code=r["reason_code"],
                        details=r["details"],
                        timestamp=datetime.fromisoformat(r["timestamp"])
                    )
                    for r in cur.fetchall()
                ]
            finally:
                conn.close()

    record = append
    find_by_subscriber = list_by_subscriber

class SqlitePortOutRepository:
    def __init__(self, db: Database):
        self.db = db
        self._lock = db._lock

    def append(self, record: PortOutRecord) -> PortOutRecord:
        with self._lock:
            conn = self.db.get_connection()
            try:
                with conn:
                    conn.execute("""
                    INSERT INTO port_out_requests (request_id, subscriber_id, recipient_operator, status, requested_at, expires_at, resolved_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.request_id, record.subscriber_id, record.recipient_operator,
                        record.status, record.requested_at.isoformat(),
                        record.expires_at.isoformat(),
                        record.resolved_at.isoformat() if record.resolved_at else None
                    ))
                return record
            finally:
                conn.close()

    def find_active_by_subscriber(self, subscriber_id: str) -> Optional[PortOutRecord]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute(
                    "SELECT * FROM port_out_requests WHERE subscriber_id = ? AND status = 'COOLING' ORDER BY requested_at DESC LIMIT 1",
                    (subscriber_id,)
                )
                r = cur.fetchone()
                if not r:
                    return None
                return PortOutRecord(
                    request_id=r["request_id"],
                    subscriber_id=r["subscriber_id"],
                    recipient_operator=r["recipient_operator"],
                    status=r["status"],
                    requested_at=datetime.fromisoformat(r["requested_at"]),
                    expires_at=datetime.fromisoformat(r["expires_at"]),
                    resolved_at=datetime.fromisoformat(r["resolved_at"]) if r["resolved_at"] else None
                )
            finally:
                conn.close()

    def mark_cancelled(self, request_id: str, resolved_at: datetime) -> None:
        with self._lock:
            conn = self.db.get_connection()
            try:
                with conn:
                    conn.execute("UPDATE port_out_requests SET status = 'CANCELLED', resolved_at = ? WHERE request_id = ?", (resolved_at.isoformat(), request_id))
            finally:
                conn.close()

    def mark_finalized(self, request_id: str, resolved_at: datetime) -> None:
        with self._lock:
            conn = self.db.get_connection()
            try:
                with conn:
                    conn.execute("UPDATE port_out_requests SET status = 'PORTED_OUT', resolved_at = ? WHERE request_id = ?", (resolved_at.isoformat(), request_id))
            finally:
                conn.close()

    def resolve_active(self, subscriber_id: str, new_status: str, resolved_at: datetime) -> None:
        with self._lock:
            conn = self.db.get_connection()
            try:
                with conn:
                    conn.execute("""
                    UPDATE port_out_requests SET status = ?, resolved_at = ?
                    WHERE subscriber_id = ? AND status = 'COOLING'
                    """, (new_status, resolved_at.isoformat(), subscriber_id))
            finally:
                conn.close()

class SqliteStateTransitionRepository:
    def __init__(self, db: Database):
        self.db = db
        self._lock = db._lock

    def append(self, transition: StateTransitionRecord) -> StateTransitionRecord:
        with self._lock:
            conn = self.db.get_connection()
            try:
                with conn:
                    conn.execute("""
                    INSERT INTO state_transitions (transition_id, subscriber_id, from_state, to_state, actor, role, reason, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        transition.transition_id, transition.subscriber_id,
                        transition.from_state.value if hasattr(transition.from_state, "value") else str(transition.from_state),
                        transition.to_state.value if hasattr(transition.to_state, "value") else str(transition.to_state),
                        transition.actor,
                        transition.role.value if hasattr(transition.role, "value") else str(transition.role),
                        transition.reason,
                        transition.timestamp.isoformat()
                    ))
                return transition
            finally:
                conn.close()

    def list_by_subscriber(self, subscriber_id: str) -> List[StateTransitionRecord]:
        with self._lock:
            conn = self.db.get_connection()
            try:
                cur = conn.execute("SELECT * FROM state_transitions WHERE subscriber_id = ? ORDER BY timestamp DESC", (subscriber_id,))
                return [
                    StateTransitionRecord(
                        transition_id=r["transition_id"],
                        subscriber_id=r["subscriber_id"],
                        from_state=SubscriberState(r["from_state"]),
                        to_state=SubscriberState(r["to_state"]),
                        actor=r["actor"],
                        role=Role(r["role"]),
                        reason=r["reason"],
                        timestamp=datetime.fromisoformat(r["timestamp"])
                    )
                    for r in cur.fetchall()
                ]
            finally:
                conn.close()

def create_sqlite_subscription_service(db_path: str = "telcolane.db"):
    from src.services.subscription_service import SubscriptionService
    db = Database(db_path)
    return SubscriptionService(
        subscriber_repo=SqliteSubscriberRepository(db),
        plan_repo=SqlitePlanRepository(db),
        audit_repo=SqliteAuditRepository(db),
        billing_repo=SqliteBillingRepository(db),
        rejection_repo=SqliteRejectionRepository(db),
        port_out_repo=SqlitePortOutRepository(db),
        transition_repo=SqliteStateTransitionRepository(db)
    )

