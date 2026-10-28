from typing import Literal

from pydantic import BaseModel, ConfigDict


class PullRequest(BaseModel):
    """A PR as the GitHub API shows it. The head repository tells a fork PR from a same-repository PR."""

    model_config = ConfigDict(frozen=True)

    url: str
    base_repo: str
    head_repo: str
    head_branch: str
    base_branch: str
    state: Literal["open", "closed", "merged"]
    labels: tuple[str, ...]
    title: str
    body: str
    draft: bool
