import json
import re
from collections.abc import Callable
from typing import Any

from veil.adapters.constants.repo_name import REPO_NAME_PATTERN
from veil.adapters.redis.cache_keys import repo_list_key
from veil.adapters.redis.guarded_redis import GuardedRedis
from veil.engine.models.config.settings import Settings


class RepoListCache:
    """The list of repos of a GitHub installation, in Redis.

    The life of an entry is the setting `cache_repo_list_ttl_seconds`. The cache holds only repo names,
    in the order that GitHub gave them. It does not keep an empty list, because a new installation may get
    repos soon. It does not keep a list with a bad name either, but it still gives that list to the caller.
    If Redis is down or an entry is bad, the loader of the caller runs.
    """

    def __init__(self, cache: GuardedRedis, ttl_seconds: int):
        self._cache = cache
        self._ttl = ttl_seconds

    @classmethod
    def from_settings(cls, cache: GuardedRedis, settings: Settings) -> "RepoListCache":
        return cls(cache, ttl_seconds=settings.cache_repo_list_ttl_seconds)

    def get_or_load(
        self, installation_id: int | str, load: Callable[[], list[str]]
    ) -> list[str]:
        key = repo_list_key(installation_id)
        cached = self._cache.get_json(key)
        if cached and _is_repo_list(cached):
            return cached
        repos = load()
        if repos and _is_repo_list(repos):
            self._cache.set(key, json.dumps(repos), self._ttl)
        return repos


def _is_repo_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(repo, str) and re.fullmatch(REPO_NAME_PATTERN, repo)
        for repo in value
    )
