import subprocess
from pathlib import Path

from pydantic import BaseModel

from veil.engine import DraftPr, FixQuery
from veil.engine.constants.skip_reasons import FixKind


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            "user.name=veil-test",
            "-c",
            "user.email=veil-test@example.invalid",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
    )
    return result.stdout.decode()


class FakePullRequest(BaseModel):
    repo: str
    head: str
    base: str
    title: str
    body: str
    draft: bool
    url: str


class FakeClone(BaseModel):
    """One checkout that the Engine opened. The Fix commits come after its start branch."""

    repo: str
    path: Path
    start_branch: str


class FakeRemoteFix(BaseModel):
    """A Fix that the fake remote knows: an open PR or a Fix branch, with its labels."""

    repo: str
    kind: FixKind
    branch: str
    base: str | None
    labels: tuple[str, ...]


class FakeWorkspace:
    def __init__(self, path: Path):
        self.path = path

    def read_file(self, path: str) -> str:
        return (self.path / path).read_bytes().decode()

    def list_files(self) -> list[str]:
        return _git(self.path, "ls-files").split("\n")[:-1]

    def write_file(self, path: str, content: str) -> None:
        (self.path / path).write_bytes(content.encode())

    def commit(self, branch: str, message: str) -> None:
        _git(self.path, "checkout", "-B", branch)
        _git(self.path, "add", "-A")
        _git(self.path, "commit", "-m", message)

    def discard_changes(self) -> None:
        _git(self.path, "reset", "--hard")
        _git(self.path, "clean", "-fd")


class FakeRepoProvider:
    """Real local git repositories. No network."""

    def __init__(
        self,
        root: Path,
        repos: dict[str, dict[str, str | bytes]],
        branch_prefix: str = "gozu/fix-",
    ):
        self._root = root
        self._branch_prefix = branch_prefix
        self._clones: list[FakeClone] = []
        self.pull_requests: list[FakePullRequest] = []
        self._remote: list[FakeRemoteFix] = []
        self._open_source_prs: set[tuple[str, str]] = set()
        for name, files in repos.items():
            origin = root / "origin" / name
            origin.mkdir(parents=True)
            _git(origin, "init", "-b", "main")
            for rel, content in files.items():
                (origin / rel).parent.mkdir(parents=True, exist_ok=True)
                target = origin / rel
                if isinstance(content, bytes):
                    target.write_bytes(content)
                else:
                    target.write_text(content)
            _git(origin, "add", "-A")
            _git(origin, "commit", "-m", "init")

    # ---- set up the fake remote ----

    def seed_source_pr(
        self,
        repo: str,
        branch: str,
        files: dict[str, str | bytes] | None = None,
        is_open: bool = True,
    ) -> None:
        """Make a branch from main, as a developer does for a PR. The files change on that branch only.

        With is_open=False the PR is merged or closed, or it never existed.
        """
        origin = self._root / "origin" / repo
        _git(origin, "checkout", "-B", branch, "main")
        for rel, content in (files or {}).items():
            target = origin / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                content if isinstance(content, bytes) else content.encode()
            )
        _git(origin, "add", "-A")
        _git(origin, "commit", "--allow-empty", "-m", f"work on {branch}")
        _git(origin, "checkout", "main")
        if is_open:
            self._open_source_prs.add((repo, branch))

    def seed_pull_request(
        self,
        repo: str,
        branch: str,
        labels: tuple[str, ...],
        base: str | None = None,
    ) -> None:
        """Put an open PR in the fake remote. An earlier run or a person made it. No base means any base."""
        self._remote.append(
            FakeRemoteFix(
                repo=repo, kind="open_pr", branch=branch, base=base, labels=labels
            )
        )

    def seed_branch(self, repo: str, branch: str, labels: tuple[str, ...]) -> None:
        """Put a Fix branch that carries these labels in the fake remote. No PR is open."""
        self._remote.append(
            FakeRemoteFix(
                repo=repo, kind="fix_branch", branch=branch, base=None, labels=labels
            )
        )

    # ---- the RepoProvider interface ----

    def open_workspace(self, repo: str, branch: str) -> FakeWorkspace:
        if branch.startswith("-"):
            raise ValueError(f"Refused the branch name {branch}.")
        path = self._root / "clone" / f"{len(self._clones)}" / repo
        origin = str(self._root / "origin" / repo)
        _git(self._root, "clone", "--branch", branch, origin, str(path))
        self._clones.append(FakeClone(repo=repo, path=path, start_branch=branch))
        return FakeWorkspace(path)

    def has_open_pr(self, repo: str, branch: str) -> bool:
        return (repo, branch) in self._open_source_prs

    def find_existing_fix(self, query: FixQuery) -> FixKind | None:
        kinds = [
            r.kind
            for r in self._remote
            if r.repo == query.repo
            and query.issue_label in r.labels
            and self._matches(r, query)
        ]
        return "open_pr" if "open_pr" in kinds else (kinds[0] if kinds else None)

    @staticmethod
    def _matches(remote: FakeRemoteFix, query: FixQuery) -> bool:
        if remote.kind == "open_pr":
            return remote.base is None or remote.base == query.source_branch
        return remote.branch.startswith(query.branch_prefix)

    def open_draft_pr(self, draft: DraftPr) -> str:
        """Push the head branch to the fake origin and open a PR. Refuse any other push, as a real provider does."""
        if not draft.head.startswith(self._branch_prefix) or draft.head == draft.base:
            raise ValueError(
                f"Refused to push {draft.head} for a PR against {draft.base}."
            )
        for pr in self.pull_requests:
            if pr.repo == draft.repo and pr.head == draft.head:
                return pr.url
        clone = self._clone_with_branch(draft.repo, draft.head)
        _git(clone.path, "push", "origin", draft.head)
        url = f"https://github.example.invalid/{draft.repo}/pull/{len(self.pull_requests) + 1}"
        self._remote.append(
            FakeRemoteFix(
                repo=draft.repo,
                kind="open_pr",
                branch=draft.head,
                base=draft.base,
                labels=draft.labels,
            )
        )
        self.pull_requests.append(
            FakePullRequest(
                repo=draft.repo,
                head=draft.head,
                base=draft.base,
                title=draft.title,
                body=draft.body,
                draft=True,
                url=url,
            )
        )
        return url

    # ---- what a test can look at ----

    @property
    def workspaces_opened(self) -> int:
        return len(self._clones)

    def head_of(self, repo: str, branch: str) -> str:
        """The commit that a branch points to in the fake origin."""
        origin = self._root / "origin" / repo
        return _git(origin, "rev-parse", branch).strip()

    def commit_count_on(self, pr: FakePullRequest) -> int:
        clone = self._clone_with_branch(pr.repo, pr.head)
        return int(
            _git(clone.path, "rev-list", "--count", f"{clone.start_branch}..{pr.head}")
        )

    def commit_subjects_on(self, pr: FakePullRequest) -> list[str]:
        """The subject line of each Fix commit on the PR branch, oldest first."""
        clone = self._clone_with_branch(pr.repo, pr.head)
        out = _git(
            clone.path,
            "log",
            "--reverse",
            "--format=%s",
            f"{clone.start_branch}..{pr.head}",
        )
        return out.splitlines()

    def file_on(self, pr: FakePullRequest, path: str) -> str:
        clone = self._clone_with_branch(pr.repo, pr.head)
        return _git(clone.path, "show", f"{pr.head}:{path}")

    def changed_paths_on(self, pr: FakePullRequest) -> set[str]:
        clone = self._clone_with_branch(pr.repo, pr.head)
        out = _git(
            clone.path, "diff", "--name-only", f"{clone.start_branch}..{pr.head}"
        )
        return set(out.split())

    def _clone_with_branch(self, repo: str, branch: str) -> FakeClone:
        for clone in self._clones:
            if (
                clone.repo == repo
                and _git(clone.path, "branch", "--list", branch).strip()
            ):
                return clone
        raise LookupError(branch)
