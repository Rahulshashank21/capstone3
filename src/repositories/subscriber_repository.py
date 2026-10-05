import threading
from typing import Dict, List, Optional, Set
from src.domain.models import Subscriber, SubscriberState

class SubscriberRepository:
    """Thread-safe in-memory append/update store for telecom subscribers."""

    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers: Dict[str, Subscriber] = {}
        self._active_mobile_numbers: Set[str] = set()

    def save(self, subscriber: Subscriber) -> Subscriber:
        with self._lock:
            self._subscribers[subscriber.subscriber_id] = subscriber
            if subscriber.state == SubscriberState.ACTIVE:
                self._active_mobile_numbers.add(subscriber.mobile_number)
            elif subscriber.mobile_number in self._active_mobile_numbers and subscriber.state in [
                SubscriberState.PORTED_OUT,
                SubscriberState.TERMINATED
            ]:
                self._active_mobile_numbers.discard(subscriber.mobile_number)
            return subscriber

    def find_by_id(self, subscriber_id: str) -> Optional[Subscriber]:
        with self._lock:
            return self._subscribers.get(subscriber_id)

    def find_by_mobile(self, mobile_number: str) -> List[Subscriber]:
        with self._lock:
            return [s for s in self._subscribers.values() if s.mobile_number == mobile_number]

    def list_all(self) -> List[Subscriber]:
        with self._lock:
            return list(self._subscribers.values())

    def get_active_numbers(self) -> Set[str]:
        with self._lock:
            return set(self._active_mobile_numbers)

    def count_by_state(self, state: SubscriberState) -> int:
        with self._lock:
            return sum(1 for s in self._subscribers.values() if s.state == state)

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()
            self._active_mobile_numbers.clear()
