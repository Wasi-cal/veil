from pathlib import Path

from pydantic import BaseModel, ConfigDict

from veil.adapters.github.models.commit_author import CommitAuthor
from veil.adapters.github.token_source import TokenSource
from veil.adapters.jira.metadata_cache import MetadataCache
from veil.adapters.redis.snapshot_source import SnapshotSource
from veil.shells.shared.models.run_credentials import RunCredentials
from veil.shells.shared.models.service_urls import ServiceUrls


class ServiceDependencies(BaseModel):
    """What a worker holds for its activities. It never goes into an activity input or result.

    The credentials live here and in the activity that uses them. Temporal never stores them.
    """

    model_config = ConfigDict(
        frozen=True, arbitrary_types_allowed=True, hide_input_in_errors=True
    )

    token_source: TokenSource
    settings_source: SnapshotSource
    credentials: RunCredentials
    checkout_root: Path
    urls: ServiceUrls = ServiceUrls()
    metadata_cache: MetadataCache | None = None
    author: CommitAuthor
