import asyncio
from datetime import datetime, timezone

class EventBus:
    def __init__(self):
        self.version = 1
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self._queues: set[asyncio.Queue] = set()

    def publish(self, reason: str = "hazards_changed"):
        self.version += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()
        event = {"version": self.version, "updated_at": self.updated_at, "reason": reason}
        for queue in list(self._queues):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def subscribe(self):
        queue = asyncio.Queue(maxsize=10)
        self._queues.add(queue)
        try:
            yield queue
        finally:
            self._queues.discard(queue)

event_bus = EventBus()
