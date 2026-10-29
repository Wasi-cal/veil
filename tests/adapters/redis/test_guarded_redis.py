import socket
import threading
import time

import pytest
import redis

from tests.support.redis_server import RunningRedis
from tests.support.secret_samples import KEY_LIKE
from veil.adapters.redis.guarded_redis import GuardedRedis
from veil.engine.errors.cache_value_refused import CacheValueRefused


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def guarded(url: str, clock=None) -> GuardedRedis:
    return GuardedRedis.from_url(url, clock=clock or FakeClock())


def test_a_value_is_stored_under_a_prefixed_key_with_a_lifetime(redis_url):
    cache = guarded(redis_url)

    stored = cache.set("example", "value", ttl_seconds=60)

    assert stored is True
    assert cache.get("example") == "value"
    raw = redis.Redis.from_url(redis_url)
    assert raw.keys("*") == [b"veil:example"]
    assert 0 < raw.ttl("veil:example") <= 60


def test_a_missing_key_gives_none_and_a_delete_removes_the_value(redis_url):
    cache = guarded(redis_url)

    assert cache.get("nothing") is None
    cache.set("example", "value", ttl_seconds=60)
    cache.delete("example")
    assert cache.get("example") is None


@pytest.mark.parametrize("ttl", [0, -5])
def test_a_value_without_a_lifetime_is_refused(redis_url, ttl):
    with pytest.raises(ValueError, match="lifetime"):
        guarded(redis_url).set("example", "value", ttl_seconds=ttl)


@pytest.mark.parametrize("name", sorted(KEY_LIKE))
def test_a_value_or_a_key_that_looks_like_a_secret_is_refused_and_nothing_is_stored(
    redis_url, name
):
    sample = KEY_LIKE[name]
    cache = guarded(redis_url)

    with pytest.raises(CacheValueRefused):
        cache.set("example", f"before {sample} after", ttl_seconds=60)
    with pytest.raises(CacheValueRefused):
        cache.set(f"key-{sample}", "value", ttl_seconds=60)

    assert redis.Redis.from_url(redis_url).keys("*") == []


def test_a_counter_counts_inside_its_window_and_expires(redis_url):
    cache = guarded(redis_url)

    counts = [cache.increment("window-1", ttl_seconds=120) for _ in range(3)]

    assert counts == [1, 2, 3]
    assert 0 < redis.Redis.from_url(redis_url).ttl("veil:window-1") <= 120


def test_with_redis_stopped_a_read_a_write_and_a_count_give_nothing_and_never_raise(
    stoppable_redis: RunningRedis,
):
    cache = guarded(stoppable_redis.url)
    cache.set("example", "value", ttl_seconds=60)
    stoppable_redis.stop()

    assert cache.get("example") is None
    assert cache.set("other", "value", ttl_seconds=60) is False
    assert cache.increment("window", ttl_seconds=60) is None
    cache.delete("example")


def test_after_a_failure_redis_is_not_called_again_until_the_cool_down_has_passed():
    class Broken:
        calls = 0

        def get(self, key):
            self.calls += 1
            raise redis.ConnectionError("down")

    broken, clock = Broken(), FakeClock()
    cache = GuardedRedis(broken, clock=clock, cooldown_seconds=5)

    for _ in range(10):
        assert cache.get("example") is None
    assert broken.calls == 1

    clock.now += 5.1
    assert cache.get("example") is None
    assert broken.calls == 2


def test_the_cache_works_again_when_redis_comes_back(stoppable_redis: RunningRedis):
    clock = FakeClock()
    cache = guarded(stoppable_redis.url, clock=clock)
    stoppable_redis.stop()
    assert cache.set("example", "value", ttl_seconds=60) is False

    stoppable_redis.start()
    clock.now += 60

    assert cache.set("example", "value", ttl_seconds=60) is True
    assert cache.get("example") == "value"


def test_any_other_redis_error_is_a_miss_too(redis_url):
    raw = redis.Redis.from_url(redis_url)
    raw.lpush("veil:a_list", "x")
    cache = guarded(redis_url)

    assert cache.get("a_list") is None


def test_a_value_that_is_not_text_is_a_miss_and_never_an_error(redis_url):
    redis.Redis.from_url(redis_url).set("veil:binary", b"\xff\xfe\x00")

    assert guarded(redis_url).get("binary") is None


def test_a_counter_key_that_has_no_lifetime_gets_one(redis_url):
    raw = redis.Redis.from_url(redis_url)
    raw.incr("veil:old-window")
    assert raw.ttl("veil:old-window") == -1

    count = guarded(redis_url).increment("old-window", ttl_seconds=90)

    assert count == 2
    assert 0 < raw.ttl("veil:old-window") <= 90


def test_a_json_entry_comes_back_as_data_and_a_bad_or_missing_one_as_none(redis_url):
    cache = guarded(redis_url)
    cache.set("good", '{"a": [1, 2]}', ttl_seconds=60)
    cache.set("bad", "{not json", ttl_seconds=60)

    assert cache.get_json("good") == {"a": [1, 2]}
    assert cache.get_json("bad") is None
    assert cache.get_json("missing") is None


@pytest.mark.parametrize("ttl", [0, -5])
def test_a_value_without_a_lifetime_is_refused_with_the_error_of_the_cache(
    redis_url, ttl
):
    with pytest.raises(CacheValueRefused, match="lifetime"):
        guarded(redis_url).set("example", "value", ttl_seconds=ttl)


def test_a_redis_that_is_up_but_never_answers_costs_one_time_out_and_not_one_for_each_read():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        held = []

        def accept():
            while True:
                try:
                    held.append(listener.accept()[0])
                except OSError:
                    return

        threading.Thread(target=accept, daemon=True).start()
        cache = GuardedRedis.from_url(f"redis://127.0.0.1:{port}/0")

        started = time.monotonic()
        first = cache.get("example")
        after_first = time.monotonic() - started
        for _ in range(50):
            assert cache.get("example") is None
        after_all = time.monotonic() - started

    assert first is None
    assert after_first >= 0.2
    assert after_all - after_first < 0.2
