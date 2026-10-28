import subprocess
from pathlib import Path

from pydantic import BaseModel

from veil.engine import ExistingFix


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
    branch: str
    title: str
    body: str
    draft: bool
    url: str


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
        _git(self.path, "checkout", "-b", branch)
        _git(self.path, "add", "-A")
        _git(self.path, "commit", "-m", message)


class FakeRepoProvider:
    """Real local git repositories. No network."""

    def __init__(self, root: Path, repos: dict[str, dict[str, str | bytes]]):
        self._root = root
        self._clones: list[tuple[str, Path]] = []
        self.pull_requests: list[FakePullRequest] = []
        self._remote: list[tuple[str, ExistingFix, tuple[str, ...]]] = []
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

    def seed_pull_request(
        self, repo: str, branch: str, labels: tuple[str, ...]
    ) -> None:
        """Put an open PR in the fake remote. An earlier run or a person made it."""
        self._remote.append((repo, ExistingFix(kind="open_pr", branch=branch), labels))

    def seed_branch(self, repo: str, branch: str, labels: tuple[str, ...]) -> None:
        """Put a gozu/fix-* branch that carries these labels in the fake remote. No PR is open."""
        self._remote.append(
            (repo, ExistingFix(kind="fix_branch", branch=branch), labels)
        )

    def find_existing_fix(self, repo: str, issue_label: str) -> ExistingFix | None:
        found = [
            fix
            for r, fix, labels in self._remote
            if r == repo and issue_label in labels
        ]
        return next(
            (f for f in found if f.kind == "open_pr"), found[0] if found else None
        )

    @property
    def workspaces_opened(self) -> int:
        return len(self._clones)

    def open_workspace(self, repo: str) -> FakeWorkspace:
        clone = self._root / "clone" / f"{len(self._clones)}" / repo
        _git(self._root, "clone", str(self._root / "origin" / repo), str(clone))
        self._clones.append((repo, clone))
        return FakeWorkspace(clone)

    def open_draft_pr(
        self,
        repo: str,
        branch: str,
        title: str,
        body: str,
        labels: tuple[str, ...],
    ) -> str:
        url = (
            f"https://github.example.invalid/{repo}/pull/{len(self.pull_requests) + 1}"
        )
        self._remote.append((repo, ExistingFix(kind="open_pr", branch=branch), labels))
        self.pull_requests.append(
            FakePullRequest(
                repo=repo, branch=branch, title=title, body=body, draft=True, url=url
            )
        )
        return url

    def _clone_with(self, pr: FakePullRequest) -> Path:
        for repo, clone in self._clones:
            branches = _git(clone, "branch", "--list", pr.branch)
            if repo == pr.repo and branches.strip():
                return clone
        raise LookupError(pr.branch)

    def commit_count_on(self, pr: FakePullRequest) -> int:
        clone = self._clone_with(pr)
        return int(_git(clone, "rev-list", "--count", f"main..{pr.branch}"))

    def file_on(self, pr: FakePullRequest, path: str) -> str:
        return _git(self._clone_with(pr), "show", f"{pr.branch}:{path}")

    def changed_paths_on(self, pr: FakePullRequest) -> set[str]:
        clone = self._clone_with(pr)
        out = _git(clone, "diff", "--name-only", f"main..{pr.branch}")
        return set(out.split())
