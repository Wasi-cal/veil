from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from veil.adapters.postgres.models.settings_snapshot import SettingsSnapshot


@runtime_checkable
class SnapshotSource(Protocol):
    """Where the settings snapshot comes from. The store in PostgreSQL is the source of truth."""

    def read_version(self) -> int:
        """The number of the changes of the settings. A read of one number."""
        ...

    def read_snapshot(self, repos: Sequence[str] = ()) -> SettingsSnapshot:
        """Read the org rows and the rows of these repos, and the version, at one point in time."""
        ...
