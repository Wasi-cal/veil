import json
from typing import Any

from veil.adapters.redis.cache_keys import jira_fields_key, jira_transitions_key
from veil.adapters.redis.guarded_redis import GuardedRedis
from veil.engine.models.config.settings import Settings


class RedisJiraMetadataCache:
    """The Jira metadata of a site in Redis: the custom field ids and the transitions.

    It satisfies the MetadataCache interface of the Jira adapter. The life of an entry is the setting
    `cache_jira_metadata_ttl_seconds`. A transition list is for one project, one issue type and one
    current status. The cache never holds a credential or a ticket. An entry in a wrong shape is a miss.
    """

    def __init__(self, cache: GuardedRedis, ttl_seconds: int, site: str):
        self._cache = cache
        self._ttl = ttl_seconds
        self._site = site

    @classmethod
    def from_settings(
        cls, cache: GuardedRedis, settings: Settings
    ) -> "RedisJiraMetadataCache":
        return cls(
            cache,
            ttl_seconds=settings.cache_jira_metadata_ttl_seconds,
            site=settings.jira_site_url,
        )

    def field_ids(self) -> dict[str, str] | None:
        value = self._cache.get_json(jira_fields_key(self._site))
        if isinstance(value, dict) and all(
            isinstance(k, str) and isinstance(v, str) for k, v in value.items()
        ):
            return value
        return None

    def store_field_ids(self, ids: dict[str, str]) -> None:
        self._cache.set(jira_fields_key(self._site), json.dumps(ids), self._ttl)

    def transitions(
        self, project: str, issue_type: str, status: str
    ) -> list[dict[str, Any]] | None:
        value = self._cache.get_json(self._key(project, issue_type, status))
        if isinstance(value, list) and all(_is_transition(item) for item in value):
            return value
        return None

    def store_transitions(
        self,
        project: str,
        issue_type: str,
        status: str,
        transitions: list[dict[str, Any]],
    ) -> None:
        self._cache.set(
            self._key(project, issue_type, status), json.dumps(transitions), self._ttl
        )

    def forget_transitions(self, project: str, issue_type: str, status: str) -> None:
        self._cache.delete(self._key(project, issue_type, status))

    def _key(self, project: str, issue_type: str, status: str) -> str:
        return jira_transitions_key(self._site, project, issue_type, status)


def _is_transition(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    target = item.get("to")
    if not isinstance(target, dict):
        return False
    category = target.get("statusCategory")
    return (
        isinstance(item.get("id"), str)
        and isinstance(target.get("name"), str)
        and isinstance(category, dict)
        and isinstance(category.get("key"), str)
    )
