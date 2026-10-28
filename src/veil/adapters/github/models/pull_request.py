from pydantic import BaseModel, ConfigDict

from veil.adapters.github.constants.pr_states import PrState


class PullRequest(BaseModel):
    """A PR as the GitHub API shows it. The head repository tells a fork PR from a same-repository PR."""

    model_config = ConfigDict(frozen=True)

    url: str
    base_repo: str
    head_repo: str
    head_branch: str
    base_branch: str
    state: PrState
    labels: tuple[str, ...]
    title: str
    body: str
    draft: bool
