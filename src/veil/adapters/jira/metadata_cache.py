from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MetadataCache(Protocol):
    """A cache for the Jira metadata that every run reads again: the custom field ids and the transitions.

    A transition list is for one project, one issue type and one current status. A workflow belongs to an
    issue type, so the issue type is part of the key. The status of a ticket is never cached.
    A miss gives None. A cache that is down gives None too, and the tracker reads Jira.
    """

    def field_ids(self) -> dict[str, str] | None: ...

    def store_field_ids(self, ids: dict[str, str]) -> None: ...

    def transitions(
        self, project: str, issue_type: str, status: str
    ) -> list[dict[str, Any]] | None: ...

    def store_transitions(
        self,
        project: str,
        issue_type: str,
        status: str,
        transitions: list[dict[str, Any]],
    ) -> None: ...

    def forget_transitions(
        self, project: str, issue_type: str, status: str
    ) -> None: ...


class NoMetadataCache:
    """The default. It keeps nothing, so the tracker reads Jira every time."""

    def field_ids(self) -> dict[str, str] | None:
        return None

    def store_field_ids(self, ids: dict[str, str]) -> None:
        return None

    def transitions(
        self, project: str, issue_type: str, status: str
    ) -> list[dict[str, Any]] | None:
        return None

    def store_transitions(
        self,
        project: str,
        issue_type: str,
        status: str,
        transitions: list[dict[str, Any]],
    ) -> None:
        return None

    def forget_transitions(self, project: str, issue_type: str, status: str) -> None:
        return None
