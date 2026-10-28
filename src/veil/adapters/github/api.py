from typing import Protocol

from veil.adapters.github.models.pull_request import PullRequest


class GitHubApi(Protocol):
    """The part of the GitHub API that the repo provider needs. A PR has one of three states: open, closed or merged."""

    def find_pull_requests(
        self, repo: str, head: str | None = None, label: str | None = None
    ) -> list[PullRequest]:
        """Return the PRs of the repository in every state. Filter by head branch and by label when given.

        The head is a branch name without an owner. A PR from a fork can have the same branch name.
        """
        ...

    def create_draft_pr(
        self,
        repo: str,
        head: str,
        base: str,
        title: str,
        body: str,
        labels: tuple[str, ...],
    ) -> PullRequest:
        """Open a draft PR from a branch of the repository. Put the labels on it."""
        ...
