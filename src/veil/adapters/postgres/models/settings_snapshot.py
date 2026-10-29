from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from veil.engine.config.resolve import resolve_settings
from veil.engine.models.config.settings import Settings


class SettingsSnapshot(BaseModel):
    """The settings rows at one point in time. A run reads them once and uses them to the end.

    It is plain data. A workflow can carry it, so a retried activity uses the same values.
    The version counts the changes of the settings. A cache can put it in its key.
    """

    model_config = ConfigDict(frozen=True)

    version: int
    org: dict[str, Any]
    repos: dict[str, dict[str, Any]]

    def settings_for(
        self, repo: str | None = None, overrides: Mapping[str, Any] | None = None
    ) -> Settings:
        """The settings of a run: the code defaults, then the org rows, the repo rows and the overrides.

        A setting with no row keeps its code default. Raise KeyError for a repo that the snapshot did not read.
        """
        if repo is not None and repo not in self.repos:
            raise KeyError(f"The snapshot did not read the repo {repo}.")
        return resolve_settings(
            org=self.org,
            repo=self.repos[repo] if repo is not None else None,
            overrides=overrides,
        )
