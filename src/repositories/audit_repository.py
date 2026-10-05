import threading
from typing import List, Optional
from src.domain.models import AuditLog, Role

class AuditRepository:
    """Append-only audit log store."""

    def __init__(self):
        self._lock = threading.RLock()
        self._logs: List[AuditLog] = []

    def append(self, log: AuditLog) -> AuditLog:
        with self._lock:
            self._logs.append(log)
            return log

    def list_all(self) -> List[AuditLog]:
        with self._lock:
            return list(self._logs)

    def find_by_actor(self, actor: str) -> List[AuditLog]:
        with self._lock:
            return [l for l in self._logs if l.actor == actor]

    def find_by_reason_code(self, reason_code: str) -> List[AuditLog]:
        with self._lock:
            return [l for l in self._logs if l.reason_code == reason_code]

    def count(self) -> int:
        with self._lock:
            return len(self._logs)

