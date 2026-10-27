import subprocess
from pathlib import Path

from pydantic import BaseModel


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
        text=True,
    )
    return result.stdout


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
        return (self.path / path).read_text()

    def edit_file(self, path: str, old: str, new: str) -> None:
        target = self.path / path
        target.write_text(target.read_text().replace(old, new, 1))

    def commit(self, branch: str, message: str) -> None:
        _git(self.path, "checkout", "-b", branch)
        _git(self.path, "add", "-A")
        _git(self.path, "commit", "-m", message)


class FakeRepoProvider:
    """Real local git repos. No network."""

    def __init__(self, root: Path, repos: dict[str, dict[str, str]]):
        self._root = root
        self._clones: dict[str, Path] = {}
        self.pull_requests: list[FakePullRequest] = []
        for name, files in repos.items():
            origin = root / "origin" / name
            origin.mkdir(parents=True)
            _git(origin, "init", "-b", "main")
            for rel, content in files.items():
                (origin / rel).write_text(content)
            _git(origin, "add", "-A")
            _git(origin, "commit", "-m", "init")

    def open_workspace(self, repo: str) -> FakeWorkspace:
        clone = self._root / "clone" / repo
        _git(self._root, "clone", str(self._root / "origin" / repo), str(clone))
        self._clones[repo] = clone
        return FakeWorkspace(clone)

    def open_draft_pr(self, repo: str, branch: str, title: str, body: str) -> str:
        url = (
            f"https://github.example.invalid/{repo}/pull/{len(self.pull_requests) + 1}"
        )
        self.pull_requests.append(
            FakePullRequest(
                repo=repo, branch=branch, title=title, body=body, draft=True, url=url
            )
        )
        return url

    def commit_count_on(self, pr: FakePullRequest) -> int:
        clone = self._clones[pr.repo]
        return int(_git(clone, "rev-list", "--count", f"main..{pr.branch}"))

    def file_on(self, pr: FakePullRequest, path: str) -> str:
        return _git(self._clones[pr.repo], "show", f"{pr.branch}:{path}")
