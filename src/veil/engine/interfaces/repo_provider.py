from typing import Protocol, runtime_checkable

from veil.engine.constants.skip_reasons import FixKind
from veil.engine.interfaces.workspace import Workspace
from veil.engine.models.provider.draft_pr import DraftPr
from veil.engine.models.provider.fix_query import FixQuery


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

    def find_existing_fix(self, query: FixQuery) -> FixKind | None:
        """Return the kind of the Fix that exists for the issue label of the query, or None.

        An open PR that carries the label counts as `open_pr`. It must have the Source PR branch as its base.
        A branch that starts with the branch prefix and carries the label counts as `fix_branch`.
        If both exist, return `open_pr`.
        """
        ...

    def open_draft_pr(self, draft: DraftPr) -> str:
        """Push the branch of the draft and open a draft PR against its base. Return the URL.

        Push only the Fix branch. It starts with the branch prefix. Never push to the base branch or to the default branch.
        Never make a second PR for a branch. If a PR for the branch exists, return its URL.
        """
        ...
