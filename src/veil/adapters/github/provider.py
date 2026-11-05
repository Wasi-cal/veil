import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Self

from pydantic import SecretStr

from veil.adapters.github.api import GitHubApi
from veil.adapters.github.constants.git import REF_PREFIX
from veil.adapters.github.constants.modes import DIR_MODE
from veil.adapters.github.constants.pr_states import CLOSED, MERGED, OPEN
from veil.adapters.github.git_command import (
    git_environment,
    refuse_option_like,
    run_git,
    secret_values,
)
from veil.adapters.github.models.pull_request import PullRequest
from veil.adapters.github.workspace import GitWorkspace
from veil.engine.constants.names import (
    FIX_BRANCH,
    FIX_PR_LABEL,
    MERGED_PR,
    OLDER_FIX_BRANCH_PREFIX,
    OPEN_PR,
    FixKind,
)
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.fix.pr_text import pr_covers_ticket
from veil.engine.models.provider.fix_query import FixQuery
from veil.engine.models.provider.new_pr import NewPr


def _same_repo(head_repo: str, repo: str) -> bool:
    """GitHub names a repository without case. A deleted fork has an empty name."""
    return bool(head_repo) and head_repo.casefold() == repo.casefold()


class GitHubRepoProvider:
    """The real repo provider. Git does the checkouts and the pushes. The GitHub API does the PRs.

    Each checkout is a private temporary directory. Call `close` in a `finally` step to delete them all.
    """

    def __init__(
        self,
        token: SecretStr,
        api: GitHubApi,
        remote_url: Callable[[str], str],
        branch_prefix: str,
        temp_root: Path | None = None,
    ):
        self._token = token
        self._api = api
        self._remote_url = remote_url
        self._branch_prefix = branch_prefix
        self._pr_cache: dict[str, list[PullRequest]] = {}
        self._temp_root = temp_root
        if temp_root is not None:
            temp_root.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
        self._directories: list[Path] = []
        self._workspaces: dict[tuple[str, Path], GitWorkspace] = {}
        self._default_branches: dict[str, str] = {}

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def close(self) -> None:
        """Delete every checkout that this provider made."""
        for directory in self._directories:
            shutil.rmtree(directory, ignore_errors=True)
        self._directories.clear()
        self._workspaces.clear()

    def _pull_requests(self, repo: str) -> list[PullRequest]:
        """The PRs of the repo. One read for each repo in a run answers every ticket, so a run makes few API calls."""
        if repo not in self._pr_cache:
            self._pr_cache[repo] = self._api.find_pull_requests(repo)
        return self._pr_cache[repo]

    def has_open_pr(self, repo: str, branch: str) -> bool:
        return any(
            pr.state == OPEN
            and pr.head_branch == branch
            and _same_repo(pr.head_repo, repo)
            for pr in self._pull_requests(repo)
        )

    def find_existing_fix(self, query: FixQuery) -> FixKind | None:
        found = [
            pr
            for pr in self._pull_requests(query.repo)
            if self._is_fix_pr_of(pr, query)
            and _same_repo(pr.head_repo, query.repo)
            and pr.base_branch == query.source_branch
        ]
        if any(pr.state == OPEN for pr in found):
            return OPEN_PR
        prefixes = (query.branch_prefix, OLDER_FIX_BRANCH_PREFIX)
        if any(
            pr.state == MERGED and pr.head_branch.startswith(prefixes) for pr in found
        ):
            return MERGED_PR
        if any(
            pr.state == CLOSED
            and pr.head_branch.startswith(prefixes)
            and self._branch_exists(query.repo, pr.head_branch)
            for pr in found
        ):
            return FIX_BRANCH
        return None

    @staticmethod
    def _is_fix_pr_of(pr: PullRequest, query: FixQuery) -> bool:
        """A Fix PR has the label `veil-fix` and a section for the ticket. A Fix PR from before that label has the issue label."""
        return (
            FIX_PR_LABEL in pr.labels and pr_covers_ticket(pr.body, query.ticket_key)
        ) or query.issue_label in pr.labels

    def _branch_exists(self, repo: str, branch: str) -> bool:
        with tempfile.TemporaryDirectory(
            prefix="veil-", dir=self._temp_root
        ) as scratch:
            listing = run_git(
                Path(scratch),
                git_environment(self._token, Path(scratch)),
                secret_values(self._token),
                "ls-remote",
                "--heads",
                "--",
                self._remote_url(repo),
                f"{REF_PREFIX}{branch}",
            )
        return bool(listing.strip())

    def open_workspace(self, repo: str, branch: str) -> GitWorkspace:
        refuse_option_like(branch)
        directory = Path(tempfile.mkdtemp(prefix="veil-", dir=self._temp_root))
        env = git_environment(self._token, directory)
        secrets = secret_values(self._token)
        checkout = directory / "checkout"
        try:
            run_git(
                directory,
                env,
                secrets,
                "clone",
                "--depth",
                "1",
                "--single-branch",
                "--no-tags",
                "--branch",
                branch,
                "--",
                self._remote_url(repo),
                str(checkout),
            )
        except BaseException:
            shutil.rmtree(directory, ignore_errors=True)
            raise
        self._directories.append(directory)
        workspace = GitWorkspace(checkout, env, secrets)
        self._workspaces[(repo, workspace.path)] = workspace
        return workspace

    def _default_branch(self, repo: str) -> str:
        """Ask GitHub once for each repo. The answer does not change during a run."""
        if repo not in self._default_branches:
            self._default_branches[repo] = self._api.default_branch(repo)
        return self._default_branches[repo]

    def open_pr(self, new_pr: NewPr) -> str:
        refuse_option_like(new_pr.head)
        if (
            not new_pr.head.startswith(self._branch_prefix)
            or new_pr.head == new_pr.base
        ):
            raise RepoProviderError(
                f"Refused to push {new_pr.head} for a PR against {new_pr.base}."
            )
        default = self._default_branch(new_pr.repo)
        if default in (new_pr.head, new_pr.base):
            raise RepoProviderError(
                f"Refused to open a PR for the default branch {default} of {new_pr.repo}."
            )
        for pr in self._api.find_pull_requests(new_pr.repo, head=new_pr.head):
            if pr.state == OPEN and _same_repo(pr.head_repo, new_pr.repo):
                return pr.url
        for (repo, _), workspace in self._workspaces.items():
            if repo == new_pr.repo and workspace.has_branch(new_pr.head):
                workspace.push(new_pr.head)
                break
        else:
            raise RepoProviderError(
                f"No checkout of {new_pr.repo} holds the branch {new_pr.head}."
            )
        created = self._api.create_pr(
            new_pr.repo,
            new_pr.head,
            new_pr.base,
            new_pr.title,
            new_pr.body,
            new_pr.labels,
        )
        self._pr_cache.pop(new_pr.repo, None)  # The new PR changes the answer.
        return created.url
