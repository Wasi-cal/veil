import subprocess
from pathlib import Path

from pydantic import SecretStr

from veil.adapters.github.provider import GitHubRepoProvider

TOKEN = "".join(["ghp_", "a1B2c3D4e5F6g7H8i9J0", "k1L2m3N4o5P6q7R8s9T0"])  # noqa: FLY002


def git(cwd: Path, *args: str) -> str:
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


def make_remote(
    root: Path,
    repo: str = "acme/app",
    branches: dict[str, dict[str, str]] | None = None,
) -> Path:
    """A bare git remote. It holds main with two commits and each extra branch with one more commit."""
    bare = root / "remotes" / f"{repo}.git"
    bare.mkdir(parents=True)
    git(bare, "init", "--bare", "-b", "main")
    work = root / "seed" / repo
    work.mkdir(parents=True)
    git(work, "init", "-b", "main")
    for number, text in enumerate(["one", "two"]):
        (work / "app.py").write_text(f"value = '{text}'\n")
        git(work, "add", "-A")
        git(work, "commit", "-m", f"commit {number}")
    for name, files in (branches or {}).items():
        git(work, "checkout", "-B", name, "main")
        for rel, content in files.items():
            (work / rel).write_text(content)
        git(work, "add", "-A")
        git(work, "commit", "--allow-empty", "-m", f"work on {name}")
    git(work, "remote", "add", "origin", bare.as_uri())
    git(work, "push", "--all", "origin")
    return bare


def make_provider(root: Path, api=None, branch_prefix: str = "gozu/fix-"):
    return GitHubRepoProvider(
        token=SecretStr(TOKEN),
        api=api,
        remote_url=lambda repo: (root / "remotes" / f"{repo}.git").as_uri(),
        branch_prefix=branch_prefix,
        temp_root=root / "tmp",
    )
