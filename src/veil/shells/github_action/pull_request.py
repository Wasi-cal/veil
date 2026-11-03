import json
from pathlib import Path

from veil.shells.github_action.constants.environment import (
    EVENT_FILE_MAX_BYTES,
    EVENT_PATH_VARIABLE,
)
from veil.shells.github_action.constants.messages import BAD_EVENT_FILE, NO_EVENT_FILE
from veil.shells.github_action.errors.action_failure import ActionFailure
from veil.shells.github_action.models.pull_request_head import PullRequestHead


def read_pull_request_head(path: Path | None) -> PullRequestHead:
    """Read the head of the pull request from the event file of the runner.

    Raise ActionFailure if the file is missing or does not hold the head. The text of the file is not trusted.
    The Action reads two fields and keeps nothing else.
    """
    if path is None or not path.is_file():
        raise ActionFailure(NO_EVENT_FILE.format(name=EVENT_PATH_VARIABLE))
    if path.stat().st_size > EVENT_FILE_MAX_BYTES:
        raise ActionFailure(BAD_EVENT_FILE)
    try:
        head = json.loads(path.read_text())["pull_request"]["head"]
        branch = head["ref"]
        repo = (head.get("repo") or {}).get("full_name") or ""
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise ActionFailure(BAD_EVENT_FILE) from None
    if not isinstance(branch, str) or not branch or not isinstance(repo, str):
        raise ActionFailure(BAD_EVENT_FILE)
    return PullRequestHead(branch=branch, repo=repo)
