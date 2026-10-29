import json
import time
from collections.abc import Callable
from typing import Any, TypeVar

import redis

from veil.adapters.redis.constants.keys import KEY_PREFIX
from veil.adapters.redis.constants.timing import (
    COOLDOWN_SECONDS,
    NO_EXPIRY,
    SOCKET_TIMEOUT_SECONDS,
)
from veil.engine.constants.secrets import SECRET_PATTERNS
from veil.engine.errors.cache_value_refused import CacheValueRefused

T = TypeVar("T")


class GuardedRedis:
    """Redis for a cache. A Redis that is down never stops a run.

    Every call has a short time-out. A call that fails gives a miss and does not raise.
    After a failed connection the client leaves Redis alone for a cool-down, so a dead Redis costs
    one failed call and not one for each read. The client refuses to store a key or a value that looks
    like a secret. It refuses a value with no lifetime too, with CacheValueRefused.
    """

    def __init__(
        self,
        client: Any,
        clock: Callable[[], float] = time.monotonic,
        cooldown_seconds: float = COOLDOWN_SECONDS,
    ):
        self._client = client
        self._clock = clock
        self._cooldown = cooldown_seconds
        self._down_until = 0.0

    @classmethod
    def from_url(cls, url: str, **options: Any) -> "GuardedRedis":
        """Connect with short time-outs. The options are the clock and the cool-down."""
        client = redis.Redis.from_url(
            url,
            socket_connect_timeout=SOCKET_TIMEOUT_SECONDS,
            socket_timeout=SOCKET_TIMEOUT_SECONDS,
            decode_responses=True,
        )
        return cls(client, **options)

    def get(self, key: str) -> str | None:
        return self._or_fallback(lambda: self._client.get(KEY_PREFIX + key), None)

    def get_json(self, key: str) -> Any:
        """The data in a JSON entry. A missing entry or an entry that is not JSON gives None."""
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set(self, key: str, value: str, ttl_seconds: int) -> bool:
        """Store a value for a lifetime. Give False when Redis is down. Raise CacheValueRefused for a secret."""
        _refuse_unsafe(key, value, ttl_seconds)
        return self._or_fallback(
            lambda: bool(self._client.set(KEY_PREFIX + key, value, ex=ttl_seconds)),
            False,
        )

    def delete(self, key: str) -> None:
        self._or_fallback(lambda: self._client.delete(KEY_PREFIX + key), None)

    def increment(self, key: str, ttl_seconds: int) -> int | None:
        """Add one to a counter, and give the new count. A counter always expires after the lifetime.

        It works on every version of Redis from 2.6.12. Give None when Redis is down.
        """
        _refuse_unsafe(key, "", ttl_seconds)
        full_key = KEY_PREFIX + key

        def add_one() -> int:
            pipeline = self._client.pipeline()
            pipeline.set(full_key, 0, ex=ttl_seconds, nx=True)
            pipeline.incr(full_key)
            pipeline.ttl(full_key)
            _, count, remaining = pipeline.execute()
            if remaining == NO_EXPIRY:
                self._client.expire(full_key, ttl_seconds)
            return int(count)

        return self._or_fallback(add_one, None)

    def _or_fallback(self, action: Callable[[], T], fallback: T) -> T:
        """Run a Redis call. If Redis fails, give the fallback. A lost connection starts the cool-down."""
        if self._clock() < self._down_until:
            return fallback
        try:
            return action()
        except (redis.ConnectionError, redis.TimeoutError):
            self._down_until = self._clock() + self._cooldown
            return fallback
        except (redis.RedisError, UnicodeDecodeError):
            return fallback


def _refuse_unsafe(key: str, value: str, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        raise CacheValueRefused(
            "A cache entry needs a lifetime of at least one second."
        )
    for text in (key, value):
        if any(pattern.search(text) for _, pattern in SECRET_PATTERNS):
            raise CacheValueRefused("The cache refuses text that looks like a secret.")
