"""Async Event Bus for real-time decoupled event publishing and subscription."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

DEFAULT_QUEUE_MAXSIZE: Final[int] = 100


@dataclass(frozen=True)
class ContextChangeEvent:
    """Event emitted whenever a .context/ file changes on disk or via API."""

    filename: str
    event_type: str  # 'disk_modified', 'api_update'
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Thread-safe and async-safe publish-subscribe event dispatcher with bounded queues."""

    def __init__(self, queue_maxsize: int = DEFAULT_QUEUE_MAXSIZE) -> None:
        self.queue_maxsize = queue_maxsize
        self._subscribers: set[asyncio.Queue[ContextChangeEvent]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[ContextChangeEvent]:
        """Subscribes to all events and returns a bounded queue receiving events."""
        queue: asyncio.Queue[ContextChangeEvent] = asyncio.Queue(maxsize=self.queue_maxsize)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[ContextChangeEvent]) -> None:
        """Removes a subscriber queue."""
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, event: ContextChangeEvent) -> None:
        """Publishes an event to all active subscriber queues, discarding oldest if full."""
        async with self._lock:
            subscribers_snapshot = list(self._subscribers)

        for queue in subscribers_snapshot:
            if queue.full():
                try:
                    queue.get_nowait()  # Evict oldest event to make room
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass


# Global singleton event bus instance
global_event_bus = EventBus()
