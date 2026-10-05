import threading
from typing import Dict, List, Optional
from datetime import datetime, timezone
from src.domain.models import RejectionRecord

class RejectionRepository:
    """Thread-safe in-memory store for activation and lifecycle rejection records (AC-09)."""

    def __init__(self):
        self._lock = threading.RLock()
        self._rejections: Dict[str, RejectionRecord] = {}

    def append(self, rejection: RejectionRecord) -> RejectionRecord:
        with self._lock:
            self._rejections[rejection.rejection_id] = rejection
            return rejection

    def find_by_id(self, rejection_id: str) -> Optional[RejectionRecord]:
        with self._lock:
            return self._rejections.get(rejection_id)

    def list_by_subscriber(self, subscriber_id: str) -> List[RejectionRecord]:
        with self._lock:
            return [r for r in self._rejections.values() if r.subscriber_id == subscriber_id]

    def list_all(self) -> List[RejectionRecord]:
        with self._lock:
            return list(self._rejections.values())

    def count(self) -> int:
        with self._lock:
            return len(self._rejections)
