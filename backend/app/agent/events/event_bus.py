"""Ordered, thread-safe synchronous publish/subscribe event bus."""

from __future__ import annotations

import logging
from collections.abc import Callable
from threading import RLock
from uuid import uuid4

from .event_models import BaseAgentEvent
from .event_types import EventType

logger = logging.getLogger(__name__)
EventSubscriber = Callable[[BaseAgentEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[tuple[str, EventSubscriber]]] = {}
        self._lock = RLock()

    def subscribe(self, event_type: EventType, subscriber: EventSubscriber) -> str:
        subscription_id = str(uuid4())
        with self._lock:
            self._subscribers.setdefault(event_type, []).append((subscription_id, subscriber))
        logger.info("Event subscriber registered: type=%s subscription=%s", event_type.value, subscription_id)
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        with self._lock:
            for subscribers in self._subscribers.values():
                for index, (current_id, _) in enumerate(subscribers):
                    if current_id == subscription_id:
                        subscribers.pop(index)
                        logger.info("Event subscriber removed: subscription=%s", subscription_id)
                        return True
        return False

    def publish(self, event: BaseAgentEvent) -> None:
        with self._lock:
            subscribers = list(self._subscribers.get(event.event_type, ()))
        logger.info("Publishing event id=%s type=%s subscribers=%d", event.event_id, event.event_type.value, len(subscribers))
        for _, subscriber in subscribers:
            subscriber(event)
