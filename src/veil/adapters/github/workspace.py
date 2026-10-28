from pathlib import Path

from veil.adapters.github.git_command import refuse_option_like, run_git
from veil.engine.errors.repo_provider_error import RepoProviderError


class GitWorkspace:
    """One private git checkout. It satisfies the Workspace interface of the Engine."""

    def __init__(self, path: Path, env: dict[str, str], secrets: tuple[str, ...]):
        self.path = path
        self._env = env
        self._secrets = secrets

    def _git(self, *args: str) -> str:
        return run_git(self.path, self._env, self._secrets, *args)

    def _inside(self, path: str) -> Path:
        """Return the full path of a file in the checkout. Refuse a path that leaves the checkout.

        This covers `..`, an absolute path and a symlink that points outside.
        """
        target = (self.path / path).resolve()
        if Path(path).is_absolute() or not target.is_relative_to(self.path.resolve()):
            raise RepoProviderError("Refused a path outside the checkout.")
        return target

    def read_file(self, path: str) -> str:
        return self._inside(path).read_bytes().decode()

    def list_files(self) -> list[str]:
        return [name for name in self._git("ls-files", "-z").split("\0") if name]

    def write_file(self, path: str, content: str) -> None:
        self._inside(path).write_bytes(content.encode())

    def commit(self, branch: str, message: str) -> None:
        refuse_option_like(branch)
        self._git("checkout", "-B", branch)
        self._git("add", "-A")
        self._git("commit", "-m", message)

    def has_branch(self, branch: str) -> bool:
        return bool(self._git("branch", "--list", "--", branch).strip())

    def push(self, branch: str) -> None:
        """Push one local branch to the branch of the same name. Never force. Never push another ref."""
        refuse_option_like(branch)
        ref = f"refs/heads/{branch}"
        self._git("push", "origin", f"{ref}:{ref}")

    def discard_changes(self) -> None:
        self._git("restore", "--source=HEAD", "--staged", "--worktree", ".")
        self._git("clean", "-fd")
