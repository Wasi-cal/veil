import threading

import redis

from veil.adapters.redis.guarded_redis import GuardedRedis
from veil.adapters.redis.rate_limiter import ModelCallLimiter
from veil.engine import Settings


class FakeTime:
    """A clock and a sleep that move together. A sleep makes the clock jump."""

    def __init__(self, now: float = 6000.0):
        self.now = now
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def limiter(url, fake_time, limit=5, local=2, cooldown=0.0):
    cache = GuardedRedis.from_url(url, clock=fake_time.clock, cooldown_seconds=cooldown)
    return ModelCallLimiter(
        cache,
        limit_per_minute=limit,
        local_limit_per_minute=local,
        clock=fake_time.clock,
        sleep=fake_time.sleep,
    )


def test_calls_up_to_the_limit_start_at_once_and_the_next_one_waits_for_the_next_minute(
    redis_url,
):
    fake_time = FakeTime(now=6010.0)
    worker = limiter(redis_url, fake_time, limit=3)

    waits = [worker.reserve() for _ in range(4)]

    assert waits[:3] == [0.0, 0.0, 0.0]
    assert waits[3] == 50.0


def test_acquire_sleeps_until_the_next_minute_and_then_goes(redis_url):
    fake_time = FakeTime(now=6010.0)
    worker = limiter(redis_url, fake_time, limit=1)
    worker.acquire()

    worker.acquire()

    assert fake_time.slept == [50.0]
    assert fake_time.now == 6060.0


def test_workers_share_one_count(redis_url):
    fake_time = FakeTime(now=6010.0)
    first, second = (
        limiter(redis_url, fake_time, limit=5),
        limiter(redis_url, fake_time, limit=5),
    )

    waits = [first.reserve(), first.reserve(), first.reserve()]
    waits += [second.reserve(), second.reserve(), second.reserve()]

    assert waits == [0.0, 0.0, 0.0, 0.0, 0.0, 50.0]


def test_a_new_minute_starts_a_new_count(redis_url):
    fake_time = FakeTime(now=6010.0)
    worker = limiter(redis_url, fake_time, limit=1)
    worker.reserve()
    assert worker.reserve() > 0

    fake_time.now = 6060.5

    assert worker.reserve() == 0.0


def test_the_counters_expire_and_nothing_else_is_stored(redis_url):
    fake_time = FakeTime()
    limiter(redis_url, fake_time).reserve()

    raw = redis.Redis.from_url(redis_url)
    [key] = raw.keys("*")
    assert key.decode().startswith("veil:rate:")
    assert 0 < raw.ttl(key) <= 120


def test_with_redis_stopped_each_worker_keeps_to_its_own_local_limit(stoppable_redis):
    fake_time = FakeTime(now=6010.0)
    worker = limiter(stoppable_redis.url, fake_time, limit=100, local=2)
    stoppable_redis.stop()

    waits = [worker.reserve() for _ in range(3)]

    assert waits == [0.0, 0.0, 50.0]


def test_the_local_limit_also_resets_each_minute(stoppable_redis):
    fake_time = FakeTime(now=6010.0)
    worker = limiter(stoppable_redis.url, fake_time, limit=100, local=1)
    stoppable_redis.stop()
    worker.reserve()
    assert worker.reserve() > 0

    fake_time.now = 6061.0

    assert worker.reserve() == 0.0


def test_when_redis_comes_back_the_shared_count_applies_again(stoppable_redis):
    fake_time = FakeTime(now=6010.0)
    worker = limiter(stoppable_redis.url, fake_time, limit=2, local=1, cooldown=1.0)
    stoppable_redis.stop()
    assert worker.reserve() == 0.0

    stoppable_redis.start()
    fake_time.now = 6061.0
    waits = [worker.reserve() for _ in range(3)]

    assert waits == [0.0, 0.0, 59.0]


def test_the_limits_come_from_the_settings_and_the_local_limit_shares_the_limit_between_workers(
    redis_url,
):
    settings = Settings(model_calls_per_minute=10, max_concurrent_runs=3)
    fake_time = FakeTime()

    worker = ModelCallLimiter.from_settings(
        GuardedRedis.from_url(redis_url),
        settings,
        clock=fake_time.clock,
        sleep=fake_time.sleep,
    )

    assert worker.limit_per_minute == 10
    assert worker.local_limit_per_minute == 4


def test_a_local_limit_is_at_least_one_call(redis_url):
    settings = Settings(model_calls_per_minute=1, max_concurrent_runs=20)

    worker = ModelCallLimiter.from_settings(GuardedRedis.from_url(redis_url), settings)

    assert worker.local_limit_per_minute == 1


def test_threads_of_one_worker_share_the_local_limit_without_losing_a_count(
    stoppable_redis,
):
    fake_time = FakeTime(now=6010.0)
    worker = limiter(stoppable_redis.url, fake_time, limit=100, local=10)
    stoppable_redis.stop()
    waits = []
    gate = threading.Barrier(40)

    def call():
        gate.wait()
        waits.append(worker.reserve())

    threads = [threading.Thread(target=call) for _ in range(40)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert waits.count(0.0) == 10
