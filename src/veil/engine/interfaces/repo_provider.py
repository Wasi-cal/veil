from typing import Protocol, runtime_checkable

from veil.engine.interfaces.workspace import Workspace
from veil.engine.models.provider.draft_pr import DraftPr
from veil.engine.models.provider.existing_fix import ExistingFix


@runtime_checkable
class RepoProvider(Protocol):
    def open_workspace(self, repo: str, branch: str) -> Workspace:
        """Open a private checkout of this branch. The branch is the branch of the Source PR.

        Treat the branch name as data. Refuse a name that git can read as an option, for example a name that starts with a dash.
        """
        ...

    def has_open_pr(self, repo: str, branch: str) -> bool:
        """Return True if an open PR in this repository has this branch as its head.

        This is the Source PR of a ticket. A PR from a fork does not count.
        """
        ...

    def find_existing_fix(self, repo: str, issue_label: str) -> ExistingFix | None:
        """Return the Fix that exists for this issue label in this repository, or None.

        An open PR that carries the label counts as `open_pr`. A gozu/fix-* branch that carries the label counts as `fix_branch`.
        If both exist, return the open PR.
        """
        ...

    def open_draft_pr(self, draft: DraftPr) -> str:
        """Push the branch of the draft and open a draft PR against its base. Return the URL.

        Push only the gozu/fix-* branch. Never push to the base branch or to the default branch.
        Never make a second PR for a branch. If a PR for the branch exists, return its URL.
        """
        ...
