import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Self

from pydantic import SecretStr

from veil.adapters.github.api import GitHubApi
from veil.adapters.github.constants.git import REF_PREFIX
from veil.adapters.github.constants.modes import DIR_MODE
from veil.adapters.github.constants.pr_states import CLOSED, OPEN
from veil.adapters.github.git_command import (
    git_environment,
    refuse_option_like,
    run_git,
    secret_values,
)
from veil.adapters.github.workspace import GitWorkspace
from veil.engine.constants.fix_kinds import FIX_BRANCH, OPEN_PR, FixKind
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.models.provider.draft_pr import DraftPr
from veil.engine.models.provider.fix_query import FixQuery


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
        self._temp_root = temp_root
        if temp_root is not None:
            temp_root.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
        self._directories: list[Path] = []
        self._workspaces: dict[tuple[str, Path], GitWorkspace] = {}

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

    def has_open_pr(self, repo: str, branch: str) -> bool:
        return any(
            pr.state == OPEN and _same_repo(pr.head_repo, repo)
            for pr in self._api.find_pull_requests(repo, head=branch)
        )

    def find_existing_fix(self, query: FixQuery) -> FixKind | None:
        found = [
            pr
            for pr in self._api.find_pull_requests(query.repo, label=query.issue_label)
            if _same_repo(pr.head_repo, query.repo)
            and pr.base_branch == query.source_branch
        ]
        if any(pr.state == OPEN for pr in found):
            return OPEN_PR
        if any(
            pr.state == CLOSED
            and pr.head_branch.startswith(query.branch_prefix)
            and self._branch_exists(query.repo, pr.head_branch)
            for pr in found
        ):
            return FIX_BRANCH
        return None

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

    def open_draft_pr(self, draft: DraftPr) -> str:
        refuse_option_like(draft.head)
        if not draft.head.startswith(self._branch_prefix) or draft.head == draft.base:
            raise RepoProviderError(
                f"Refused to push {draft.head} for a PR against {draft.base}."
            )
        for pr in self._api.find_pull_requests(draft.repo, head=draft.head):
            if pr.state == OPEN and _same_repo(pr.head_repo, draft.repo):
                return pr.url
        for (repo, _), workspace in self._workspaces.items():
            if repo == draft.repo and workspace.has_branch(draft.head):
                workspace.push(draft.head)
                break
        else:
            raise RepoProviderError(
                f"No checkout of {draft.repo} holds the branch {draft.head}."
            )
        return self._api.create_draft_pr(
            draft.repo, draft.head, draft.base, draft.title, draft.body, draft.labels
        ).url
