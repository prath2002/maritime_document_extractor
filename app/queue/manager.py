import asyncio


class QueueManager:
    def __init__(self, *, max_depth: int):
        self.max_depth = max_depth
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=max_depth)
        self._closed = False

    @property
    def current_depth(self) -> int:
        return self._queue.qsize()

    async def health_check(self) -> tuple[str, str | None]:
        if self._closed:
            return "DEGRADED", "Queue manager has been closed."
        return "OK", f"In-memory queue initialized with max depth {self.max_depth}."

    async def close(self) -> None:
        self._closed = True
