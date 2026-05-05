from collections import deque
from threading import Lock
import time


class RateLimiter:
    def __init__(self, max_actions: int = 10, per_seconds: float = 1.0) -> None:
        self._max_actions = max_actions
        self._per_seconds = per_seconds
        self._timestamps: deque[float] = deque()
        self._lock = Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._timestamps and now - self._timestamps[0] > self._per_seconds:
                self._timestamps.popleft()

            if len(self._timestamps) >= self._max_actions:
                return False

            self._timestamps.append(now)
            return True
