import re
from collections.abc import Sequence

from pydantic import ValidationError

from veil.adapters.postgres.models.settings_snapshot import SettingsSnapshot
from veil.adapters.redis.cache_keys import settings_key
from veil.adapters.redis.constants.keys import NAMESPACE_PATTERN
from veil.adapters.redis.guarded_redis import GuardedRedis
from veil.adapters.redis.snapshot_source import SnapshotSource
from veil.engine.errors.settings_error import SettingsError


class CachedSettingsStore:
    """The settings snapshot with a cache in front of the database.

    A run asks the database for the version number, which is one small read. The key holds the version.
    So a write makes the old entry stale at once, and the next read finds no entry and reads the database.
    The key also holds the namespace of the deployment, so two deployments can share one Redis.
    When Redis is down or an entry is bad, the read goes to the database. Nothing fails.
    The lifetime of an entry is the setting `cache_settings_ttl_seconds`.
    """

    def __init__(self, source: SnapshotSource, cache: GuardedRedis, namespace: str):
        if not re.fullmatch(NAMESPACE_PATTERN, namespace):
            raise ValueError(
                "The cache namespace has 1 to 40 letters, digits, dots, dashes or underscores."
            )
        self._source = source
        self._cache = cache
        self._namespace = namespace

    def read_snapshot(self, repos: Sequence[str] = ()) -> SettingsSnapshot:
        version = self._source.read_version()
        cached = self._cache.get(settings_key(self._namespace, version, repos))
        if cached is not None:
            try:
                snapshot = SettingsSnapshot.model_validate_json(cached)
            except ValidationError:
                snapshot = None
            if snapshot is not None and snapshot.version == version:
                return snapshot
        snapshot = self._source.read_snapshot(repos)
        self._remember(snapshot, repos)
        return snapshot

    def _remember(self, snapshot: SettingsSnapshot, repos: Sequence[str]) -> None:
        """Store the snapshot under its own version. A write may have landed since the version was read."""
        try:
            lifetime = snapshot.settings_for().cache_settings_ttl_seconds
        except SettingsError:
            return
        self._cache.set(
            settings_key(self._namespace, snapshot.version, repos),
            snapshot.model_dump_json(),
            lifetime,
        )
