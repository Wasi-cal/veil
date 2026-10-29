import pytest
import redis

from veil.adapters.redis.guarded_redis import GuardedRedis
from veil.adapters.redis.repo_list_cache import RepoListCache
from veil.engine import Settings

REPOS = ["acme/app", "acme/web", "acme/.github"]


def repo_cache(url, ttl=600):
    return RepoListCache(GuardedRedis.from_url(url), ttl_seconds=ttl)


class Loader:
    def __init__(self, repos):
        self.repos = repos
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return list(self.repos)


def test_the_list_is_loaded_once_and_then_comes_from_redis_in_the_same_order(redis_url):
    cache, load = repo_cache(redis_url), Loader(REPOS)

    first = cache.get_or_load(42, load)
    second = cache.get_or_load(42, load)

    assert first == second == REPOS
    assert load.calls == 1


def test_each_installation_has_its_own_list(redis_url):
    cache = repo_cache(redis_url)

    cache.get_or_load(1, Loader(["acme/one"]))

    assert cache.get_or_load(2, Loader(["acme/two"])) == ["acme/two"]


def test_the_entry_lives_for_the_repo_list_lifetime_of_the_settings(redis_url):
    repo_cache(redis_url, ttl=90).get_or_load(42, Loader(REPOS))

    raw = redis.Redis.from_url(redis_url)
    [key] = raw.keys("veil:repos:*")
    assert 0 < raw.ttl(key) <= 90


def test_an_entry_that_cannot_be_read_is_loaded_again_and_replaced(redis_url):
    cache, load = repo_cache(redis_url), Loader(REPOS)
    cache.get_or_load(42, load)
    raw = redis.Redis.from_url(redis_url)
    [key] = raw.keys("veil:repos:*")
    raw.set(key, '{"not": "a list"}')

    assert cache.get_or_load(42, load) == REPOS
    assert load.calls == 2


@pytest.mark.parametrize("bad", ["not a repo", "acme/a b", "../etc/passwd", ""])
def test_a_list_with_something_that_is_not_a_repo_name_is_returned_but_never_stored(
    redis_url, bad
):
    load = Loader(["acme/app", bad])

    repos = repo_cache(redis_url).get_or_load(42, load)

    assert repos == ["acme/app", bad]
    assert redis.Redis.from_url(redis_url).keys("*") == []


def test_an_empty_list_is_not_stored_so_a_new_installation_is_asked_again(redis_url):
    cache, load = repo_cache(redis_url), Loader([])

    assert cache.get_or_load(42, load) == []
    assert cache.get_or_load(42, load) == []

    assert load.calls == 2
    assert redis.Redis.from_url(redis_url).keys("*") == []


def test_the_lifetime_comes_from_the_settings(redis_url):
    settings = Settings(cache_repo_list_ttl_seconds=77)

    RepoListCache.from_settings(GuardedRedis.from_url(redis_url), settings).get_or_load(
        42, Loader(REPOS)
    )

    raw = redis.Redis.from_url(redis_url)
    [key] = raw.keys("veil:repos:*")
    assert 0 < raw.ttl(key) <= 77


def test_with_redis_stopped_the_list_is_loaded_every_time_and_nothing_fails(
    stoppable_redis,
):
    cache, load = repo_cache(stoppable_redis.url), Loader(REPOS)
    cache.get_or_load(42, load)
    stoppable_redis.stop()

    assert cache.get_or_load(42, load) == REPOS
    assert cache.get_or_load(42, load) == REPOS
    assert load.calls == 3
