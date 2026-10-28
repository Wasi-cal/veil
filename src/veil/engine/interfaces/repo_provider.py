from typing import Protocol, runtime_checkable

from veil.engine.interfaces.workspace import Workspace
from veil.engine.models.provider.existing_fix import ExistingFix


@runtime_checkable
class RepoProvider(Protocol):
    def open_workspace(self, repo: str) -> Workspace: ...
    def find_existing_fix(self, repo: str, issue_label: str) -> ExistingFix | None:
        """Return the Fix that exists for this issue label in this repository, or None.

        An open PR that carries the label counts as `open_pr`. A gozu/fix-* branch that carries the label counts as `fix_branch`.
        If both exist, return the open PR.
        """
        ...

    def open_draft_pr(
        self, repo: str, branch: str, title: str, body: str, labels: tuple[str, ...]
    ) -> str:
        """Push the branch and open a draft PR with these labels. Return the URL.

        Never make a second PR for a branch. If a PR for the branch exists, return its URL.
        """
        ...
