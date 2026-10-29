"""The layout of every key in Redis. All keys are built here, so no two uses can clash."""

import hashlib
from collections.abc import Sequence

from veil.adapters.redis.constants.keys import (
    DIGEST_LENGTH,
    JIRA_FAMILY,
    RATE_FAMILY,
    REPOS_FAMILY,
    SETTINGS_FAMILY,
    SNAPSHOT_FORMAT,
)


def digest(text: str) -> str:
    """A short fixed text for a text that may hold spaces or other characters. The digest is safe in a key."""
    return hashlib.sha256(text.encode()).hexdigest()[:DIGEST_LENGTH]


def settings_key(namespace: str, version: int, repos: Sequence[str]) -> str:
    """The snapshot of a deployment at a version, for a set of repos. The order of the repos does not matter."""
    repos_digest = digest("\n".join(sorted(set(repos))))
    return f"{SETTINGS_FAMILY}:{namespace}:{SNAPSHOT_FORMAT}:{version}:{repos_digest}"


def jira_fields_key(site: str) -> str:
    return f"{JIRA_FAMILY}:{digest(site)}:fields"


def jira_transitions_key(site: str, project: str, issue_type: str, status: str) -> str:
    scope = digest(f"{project}\n{issue_type}\n{status}")
    return f"{JIRA_FAMILY}:{digest(site)}:transitions:{scope}"


def repo_list_key(installation_id: int | str) -> str:
    return f"{REPOS_FAMILY}:{int(installation_id)}"


def rate_key(window: int) -> str:
    return f"{RATE_FAMILY}:{window}"
