from pydantic import BaseModel, ConfigDict


class PullRequestHead(BaseModel):
    """The head of the pull request that started a run: its branch and the repo that holds the branch."""

    model_config = ConfigDict(frozen=True)

    branch: str
    # The empty string means that the repo of the head is gone, for example a deleted fork.
    repo: str

    def is_from(self, repo: str) -> bool:
        """True when the branch is in this repo. GitHub names a repo without case."""
        return bool(self.repo) and self.repo.casefold() == repo.casefold()
