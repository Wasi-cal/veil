from veil.adapters.github.constants.repo_name import REPO_NAME
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.shells.service.constants.names import WORKFLOW_ID_PREFIX


def workflow_id(repo: str) -> str:
    """The workflow ID of a repo. The same repo always gives the same ID, so a second start joins the first run.

    Raise RepoProviderError for a name that is not a repo name.
    """
    if not REPO_NAME.fullmatch(repo) or ".." in repo:
        raise RepoProviderError("Refused the repository name.")
    return WORKFLOW_ID_PREFIX + repo.replace("/", "--")
