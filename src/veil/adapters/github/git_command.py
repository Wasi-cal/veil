import base64
import os
import subprocess
from pathlib import Path

from pydantic import SecretStr

from veil.adapters.github.constants.git import (
    GITHUB_URL,
    LOGIN_REFUSED_MARKERS,
    NETWORK_VARIABLES,
    TOKEN_USER,
)
from veil.adapters.github.models.commit_author import CommitAuthor
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.errors.token_expired import TokenExpired
from veil.engine.secrets.redact import redact


def refuse_option_like(name: str) -> None:
    """Treat a branch name as data. Git can read a name that starts with a dash as an option."""
    if not name or name.startswith("-"):
        raise RepoProviderError(
            "Refused the branch name. Git can read it as an option."
        )


def _basic_credential(token: SecretStr) -> str:
    return base64.b64encode(
        f"{TOKEN_USER}:{token.get_secret_value()}".encode()
    ).decode()


def secret_values(token: SecretStr) -> tuple[str, ...]:
    """The token and its base64 form in the header. Hide both in every error."""
    return (token.get_secret_value(), _basic_credential(token))


def git_environment(
    token: SecretStr, home: Path, author: CommitAuthor | None = None
) -> dict[str, str]:
    """The only variables that a git child process gets. The token goes in a per-command header.

    Git does not write this header to `.git/config`. The header is for github.com only.
    The proxy and certificate variables pass through, because git needs them to reach GitHub.
    """
    author = author or CommitAuthor()
    credential = _basic_credential(token)
    passed = {
        name: os.environ[name] for name in NETWORK_VARIABLES if name in os.environ
    }
    return {
        **passed,
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "LANG": "C",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": author.name,
        "GIT_AUTHOR_EMAIL": author.email,
        "GIT_COMMITTER_NAME": author.name,
        "GIT_COMMITTER_EMAIL": author.email,
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": f"http.{GITHUB_URL}.extraheader",
        "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {credential}",
    }


def run_git(
    cwd: Path, env: dict[str, str], secrets: tuple[str, ...], *args: str
) -> str:
    """Run git with this environment. A failure raises RepoProviderError with the credential values hidden.

    If GitHub refused the login, the error is TokenExpired, a kind of RepoProviderError.
    """
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, env=env, check=True, capture_output=True
        )
    except subprocess.CalledProcessError as failure:
        detail = failure.stderr.decode(errors="replace").strip()
        error = (
            TokenExpired
            if any(marker in detail for marker in LOGIN_REFUSED_MARKERS)
            else RepoProviderError
        )
        raise error(redact(f"git {args[0]} failed. {detail}", secrets)) from None
    return result.stdout.decode()
