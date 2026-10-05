import threading
from typing import List, Optional
from src.domain.models import BillingRecord

class BillingRepository:
    """Append-only billing transaction ledger."""

    def __init__(self):
        self._lock = threading.RLock()
        self._records: List[BillingRecord] = []

    def append(self, record: BillingRecord) -> BillingRecord:
        with self._lock:
            self._records.append(record)
            return record

    def list_by_subscriber(self, subscriber_id: str) -> List[BillingRecord]:
        with self._lock:
            return [r for r in self._records if r.subscriber_id == subscriber_id]

    def list_all(self) -> List[BillingRecord]:
        with self._lock:
            return list(self._records)

    def count(self) -> int:
        with self._lock:
            return len(self._records)

