import threading
from typing import Dict, List, Optional
from src.domain.models import PlanVersion, PlanType, PlanImmutableException

class PlanRepository:
    """Thread-safe append-only plan version catalog."""

    def __init__(self):
        self._lock = threading.RLock()
        # Keyed by (plan_id, version)
        self._catalog: Dict[str, Dict[int, PlanVersion]] = {}

    def save(self, plan: PlanVersion) -> PlanVersion:
        with self._lock:
            versions = self._catalog.setdefault(plan.plan_id, {})
            if plan.version in versions:
                existing = versions[plan.version]
                if existing.is_published:
                    raise PlanImmutableException(
                        f"Cannot overwrite published plan version '{plan.plan_id}:v{plan.version}'",
                        "ERR_PLAN_IMMUTABLE"
                    )
            versions[plan.version] = plan
            return plan

    def find_latest(self, plan_id: str) -> Optional[PlanVersion]:
        with self._lock:
            versions = self._catalog.get(plan_id)
            if not versions:
                return None
            latest_version_num = max(versions.keys())
            return versions[latest_version_num]

    def find_by_version(self, plan_id: str, version: int) -> Optional[PlanVersion]:
        with self._lock:
            versions = self._catalog.get(plan_id)
            if not versions:
                return None
            return versions.get(version)

    def list_all_latest(self) -> List[PlanVersion]:
        with self._lock:
            result = []
            for plan_id, versions in self._catalog.items():
                if versions:
                    latest_num = max(versions.keys())
                    result.append(versions[latest_num])
            return result

    def list_published(self) -> List[PlanVersion]:
        with self._lock:
            return [p for p in self.list_all_latest() if p.is_published]

    def count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._catalog.values())

    def clear(self) -> None:
        with self._lock:
            self._catalog.clear()
