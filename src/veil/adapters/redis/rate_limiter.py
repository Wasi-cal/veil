import math
import threading
import time
from collections.abc import Callable

from veil.adapters.redis.cache_keys import rate_key
from veil.adapters.redis.constants.rate import (
    RATE_KEY_LIFETIME_SECONDS,
    RATE_WINDOW_SECONDS,
)
from veil.adapters.redis.guarded_redis import GuardedRedis
from veil.engine.models.config.settings import Settings


class ModelCallLimiter:
    """The limit of model calls for each minute, shared by all workers through a counter in Redis.

    Each minute has its own counter. A call that goes over the limit waits for the next minute.
    If Redis is down, a worker counts alone against a smaller local limit. The local limit is the
    shared limit divided by the number of workers that can run at once. So the workers together
    stay near the shared limit.
    """

    def __init__(
        self,
        cache: GuardedRedis,
        limit_per_minute: int,
        local_limit_per_minute: int,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if limit_per_minute < 1 or local_limit_per_minute < 1:
            raise ValueError("A limit is at least one call for each minute.")
        self.limit_per_minute = limit_per_minute
        self.local_limit_per_minute = local_limit_per_minute
        self._cache = cache
        self._clock = clock
        self._sleep = sleep
        self._local_window = -1
        self._local_count = 0
        self._lock = threading.Lock()

    @classmethod
    def from_settings(
        cls,
        cache: GuardedRedis,
        settings: Settings,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> "ModelCallLimiter":
        local = max(
            1, math.ceil(settings.model_calls_per_minute / settings.max_concurrent_runs)
        )
        return cls(
            cache,
            limit_per_minute=settings.model_calls_per_minute,
            local_limit_per_minute=local,
            clock=clock,
            sleep=sleep,
        )

    def reserve(self) -> float:
        """Count one call. Give 0 if it may start now, or the seconds until the next minute."""
        now = self._clock()
        window = int(now // RATE_WINDOW_SECONDS)
        count = self._cache.increment(rate_key(window), RATE_KEY_LIFETIME_SECONDS)
        limit = self.limit_per_minute
        if count is None:
            count, limit = self._count_locally(window), self.local_limit_per_minute
        if count <= limit:
            return 0.0
        return (window + 1) * RATE_WINDOW_SECONDS - now

    def acquire(self) -> None:
        """Wait until a call may start."""
        while (wait := self.reserve()) > 0:
            self._sleep(wait)

    def _count_locally(self, window: int) -> int:
        """Count a call of this worker. Threads of the worker share the count, so a lock guards it."""
        with self._lock:
            if window != self._local_window:
                self._local_window, self._local_count = window, 0
            self._local_count += 1
            return self._local_count
