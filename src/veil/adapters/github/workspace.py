from pathlib import Path

from veil.adapters.github.constants.git import REF_PREFIX, SYMLINK_MODE
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

        This covers `..`, an absolute path and a path that holds a symlink.
        """
        if Path(path).is_absolute():
            raise RepoProviderError("Refused a path outside the checkout.")
        self._refuse_symlink(path)
        target = (self.path / path).resolve()
        if not target.is_relative_to(self.path.resolve()):
            raise RepoProviderError("Refused a path outside the checkout.")
        return target

    def _refuse_symlink(self, path: str) -> None:
        """Refuse a path that has a symlink in it, in the file or in a folder of the path.

        The Engine checks the text of a path. A symlink can hide the real path, for example `.github/` or `.env`.
        The error is FileNotFoundError, so the Engine treats the path as no file of the repo and goes on.
        """
        current = self.path
        for part in Path(path).parts:
            current = current / part
            if current.is_symlink():
                raise FileNotFoundError(
                    f"{path} holds a symlink. Veil does not follow symlinks."
                )

    def read_file(self, path: str) -> str:
        return self._inside(path).read_bytes().decode()

    def list_files(self) -> list[str]:
        """The files of the repo. A symlink is not in the list, because veil never follows one."""
        files = []
        for entry in self._git("ls-files", "-s", "-z").split("\0"):
            info, _, name = entry.partition("\t")
            if name and info.split()[0] != SYMLINK_MODE:
                files.append(name)
        return files

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
        ref = f"{REF_PREFIX}{branch}"
        self._git("push", "origin", f"{ref}:{ref}")

    def discard_changes(self) -> None:
        self._git("restore", "--source=HEAD", "--staged", "--worktree", ".")
        self._git("clean", "-fd")
