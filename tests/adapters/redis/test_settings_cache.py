import pytest
import redis

from tests.support.secret_samples import KEY_LIKE
from veil.adapters.postgres.store import PostgresSettingsStore
from veil.adapters.redis.guarded_redis import GuardedRedis
from veil.adapters.redis.settings_cache import CachedSettingsStore
from veil.engine import Settings

ACTOR = "alice"
NAMESPACE = "test"


class CountingStore:
    """The store, with a count of the reads that reach the database."""

    def __init__(self, store: PostgresSettingsStore):
        self._store = store
        self.snapshot_reads = 0

    def read_version(self) -> int:
        return self._store.read_version()

    def read_snapshot(self, repos=()):
        self.snapshot_reads += 1
        return self._store.read_snapshot(repos)


def build(engine, redis_url):
    store = PostgresSettingsStore(engine)
    counting = CountingStore(store)
    return (
        store,
        counting,
        CachedSettingsStore(counting, GuardedRedis.from_url(redis_url), NAMESPACE),
    )


def test_the_second_read_comes_from_redis_and_equals_the_first(engine, redis_url):
    _, counting, cached = build(engine, redis_url)

    first = cached.read_snapshot(["acme/app"])
    second = cached.read_snapshot(["acme/app"])

    assert counting.snapshot_reads == 1
    assert second == first


def test_a_write_makes_the_old_entry_stale_at_once(engine, redis_url):
    store, counting, cached = build(engine, redis_url)
    assert cached.read_snapshot().settings_for().step_cap == Settings().step_cap

    store.set_org("step_cap", 40, actor=ACTOR)
    fresh = cached.read_snapshot()

    assert fresh.settings_for().step_cap == 40
    assert counting.snapshot_reads == 2


def test_a_repo_row_change_also_shows_at_once(engine, redis_url):
    store, _, cached = build(engine, redis_url)
    cached.read_snapshot(["acme/app"])

    store.set_repo("acme/app", "step_cap", 10, actor=ACTOR)

    assert cached.read_snapshot(["acme/app"]).settings_for("acme/app").step_cap == 10


def test_each_set_of_repos_has_its_own_entry_and_the_order_does_not_matter(
    engine, redis_url
):
    _, counting, cached = build(engine, redis_url)

    cached.read_snapshot(["acme/a", "acme/b"])
    cached.read_snapshot(["acme/b", "acme/a"])
    assert counting.snapshot_reads == 1

    cached.read_snapshot(["acme/a"])
    assert counting.snapshot_reads == 2


def test_the_entry_lives_for_the_cache_lifetime_of_the_settings(engine, redis_url):
    store, _, cached = build(engine, redis_url)
    store.set_org("cache_settings_ttl_seconds", 30, actor=ACTOR)

    cached.read_snapshot()

    raw = redis.Redis.from_url(redis_url)
    [key] = raw.keys("veil:settings:*")
    assert 0 < raw.ttl(key) <= 30


def test_with_redis_stopped_every_read_comes_from_the_database_and_nothing_fails(
    engine, stoppable_redis
):
    store = PostgresSettingsStore(engine)
    counting = CountingStore(store)
    cached = CachedSettingsStore(
        counting, GuardedRedis.from_url(stoppable_redis.url), NAMESPACE
    )
    cached.read_snapshot()
    stoppable_redis.stop()

    store.set_org("step_cap", 40, actor=ACTOR)
    first = cached.read_snapshot()
    second = cached.read_snapshot()

    assert first.settings_for().step_cap == second.settings_for().step_cap == 40
    assert counting.snapshot_reads == 3


def test_a_snapshot_that_is_newer_than_the_version_read_is_stored_under_its_own_version(
    engine, redis_url
):
    store = PostgresSettingsStore(engine)

    class Racing:
        """A write lands between the read of the version and the read of the rows."""

        def read_version(self):
            version = store.read_version()
            store.set_org("step_cap", 41, actor=ACTOR)
            return version

        def read_snapshot(self, repos=()):
            return store.read_snapshot(repos)

    cached = CachedSettingsStore(Racing(), GuardedRedis.from_url(redis_url), NAMESPACE)

    snapshot = cached.read_snapshot()

    [key] = redis.Redis.from_url(redis_url).keys("veil:settings:*")
    assert key.decode().startswith(f"veil:settings:{NAMESPACE}:v1:{snapshot.version}:")
    assert snapshot.settings_for().step_cap == 41


def test_an_entry_that_cannot_be_read_is_a_miss_and_is_replaced(engine, redis_url):
    store, counting, cached = build(engine, redis_url)
    cached.read_snapshot()
    raw = redis.Redis.from_url(redis_url)
    [key] = raw.keys("veil:settings:*")
    raw.set(key, "not json at all")

    snapshot = cached.read_snapshot()

    assert snapshot.version == store.read_version()
    assert counting.snapshot_reads == 2
    assert raw.get(key) != b"not json at all"


def test_redis_holds_no_secret_after_the_reads_and_the_writes(engine, redis_url):
    store, _, cached = build(engine, redis_url)
    cached.read_snapshot(["acme/app"])
    store.set_repo("acme/app", "cheap_model", "repo-model", actor=ACTOR)
    cached.read_snapshot(["acme/app"])

    raw = redis.Redis.from_url(redis_url)
    everything = b" ".join(
        key + b" " + (raw.get(key) or b"") for key in raw.keys("*")
    ).decode()
    for sample in KEY_LIKE.values():
        assert sample not in everything


def test_the_key_of_an_entry_holds_the_version_of_the_settings(engine, redis_url):
    store, _, cached = build(engine, redis_url)
    cached.read_snapshot()
    store.set_org("step_cap", 40, actor=ACTOR)
    cached.read_snapshot()

    keys = sorted(
        key.decode() for key in redis.Redis.from_url(redis_url).keys("veil:settings:*")
    )

    version = store.read_version()
    assert len(keys) == 2
    assert keys[-1].startswith(f"veil:settings:{NAMESPACE}:v1:{version}:")
    assert keys[0].startswith(f"veil:settings:{NAMESPACE}:v1:{version - 1}:")


def test_two_deployments_that_share_one_redis_do_not_share_entries(engine, redis_url):
    store = PostgresSettingsStore(engine)
    counting = CountingStore(store)
    staging = CachedSettingsStore(counting, GuardedRedis.from_url(redis_url), "staging")
    production = CachedSettingsStore(
        counting, GuardedRedis.from_url(redis_url), "production"
    )

    staging.read_snapshot()
    production.read_snapshot()
    staging.read_snapshot()

    assert counting.snapshot_reads == 2


@pytest.mark.parametrize(
    "namespace", ["", "has space", "a" * 41, "sl/ash", "colon:name"]
)
def test_a_namespace_that_could_clash_with_the_key_layout_is_refused(
    engine, redis_url, namespace
):
    with pytest.raises(ValueError, match="namespace"):
        CachedSettingsStore(
            CountingStore(PostgresSettingsStore(engine)),
            GuardedRedis.from_url(redis_url),
            namespace,
        )
