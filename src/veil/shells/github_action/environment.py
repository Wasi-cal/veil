from collections.abc import Mapping
from pathlib import Path

from veil.adapters.github.constants.repo_name import REPO_NAME
from veil.shells.github_action.constants.environment import (
    EVENT_VARIABLE,
    REPOSITORY_VARIABLE,
    SUMMARY_VARIABLE,
    WORKSPACE_VARIABLE,
)
from veil.shells.github_action.constants.messages import (
    BAD_REPOSITORY,
    NO_REPOSITORY,
    NO_WORKSPACE,
)
from veil.shells.github_action.errors.action_failure import ActionFailure
from veil.shells.github_action.models.run_environment import RunEnvironment


def read_run_environment(environ: Mapping[str, str]) -> RunEnvironment:
    """Read the variables that the runner sets. Raise ActionFailure if one is missing or not valid."""
    repo = environ.get(REPOSITORY_VARIABLE, "")
    if not repo:
        raise ActionFailure(NO_REPOSITORY.format(name=REPOSITORY_VARIABLE))
    if not REPO_NAME.fullmatch(repo) or ".." in repo:
        raise ActionFailure(BAD_REPOSITORY.format(name=REPOSITORY_VARIABLE))
    workspace = environ.get(WORKSPACE_VARIABLE, "")
    if not workspace:
        raise ActionFailure(NO_WORKSPACE.format(name=WORKSPACE_VARIABLE))
    summary = environ.get(SUMMARY_VARIABLE)
    return RunEnvironment(
        repo=repo,
        workspace=Path(workspace),
        event=environ.get(EVENT_VARIABLE, ""),
        summary_file=Path(summary) if summary else None,
    )
