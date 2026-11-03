import os
import stat

import pytest

from tests.adapters.github.support import TOKEN, make_provider, make_remote
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.errors.token_expired import TokenExpired


@pytest.fixture
def refusing_git(tmp_path, monkeypatch):
    """A `git` that GitHub would answer with a refused login, put first on the PATH."""

    def install(stderr: str):
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir(exist_ok=True)
        script = bin_dir / "git"
        script.write_text(f"#!/bin/sh\necho '{stderr}' >&2\nexit 128\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    return install


@pytest.mark.parametrize(
    "stderr",
    [
        "remote: Invalid username or token. Password authentication is not supported.",
        "fatal: Authentication failed for 'https://github.com/acme/app.git/'",
        "fatal: unable to access 'https://github.com/acme/app.git/': The requested URL returned error: 401",
    ],
)
def test_a_refused_login_of_git_is_an_expired_token_error(
    tmp_path, refusing_git, stderr
):
    make_remote(tmp_path)
    (tmp_path / "tmp").mkdir()
    provider = make_provider(tmp_path)
    refusing_git(stderr)

    with pytest.raises(TokenExpired) as failure:
        provider.open_workspace("acme/app", "main")

    assert TOKEN not in str(failure.value)


def test_any_other_failure_of_git_is_not_an_expired_token(tmp_path, refusing_git):
    make_remote(tmp_path)
    (tmp_path / "tmp").mkdir()
    provider = make_provider(tmp_path)
    refusing_git("fatal: repository not found")

    with pytest.raises(RepoProviderError) as failure:
        provider.open_workspace("acme/app", "main")

    assert not isinstance(failure.value, TokenExpired)
