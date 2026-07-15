from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic
from typing import Callable


class InMemoryRateLimiter:
    """Small process-local limiter for sensitive endpoints.

    It is enough to protect the local/single-process app from accidental brute force.
    Production with multiple workers should replace this with Redis or another shared store.
    """

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or monotonic
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        now = self._clock()
        bucket = self._hits[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)


auth_rate_limiter = InMemoryRateLimiter()
