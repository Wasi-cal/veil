import stat

import pytest

from tests.adapters.github.support import TOKEN, git, make_provider, make_remote
from veil.engine.errors.repo_provider_error import RepoProviderError

FEATURE = {"app.py": "value = 'feature'\n"}


def provider_with_feature(tmp_path):
    make_remote(tmp_path, branches={"feature-x": FEATURE})
    (tmp_path / "tmp").mkdir()
    return make_provider(tmp_path)


def test_the_checkout_is_the_branch_of_the_source_pr(tmp_path):
    provider = provider_with_feature(tmp_path)

    workspace = provider.open_workspace("acme/app", "feature-x")

    assert workspace.read_file("app.py") == "value = 'feature'\n"
    assert workspace.list_files() == ["app.py"]


def test_the_checkout_is_shallow_and_private(tmp_path):
    provider = provider_with_feature(tmp_path)

    workspace = provider.open_workspace("acme/app", "feature-x")

    assert git(workspace.path, "rev-list", "--count", "HEAD").strip() == "1"
    mode = stat.S_IMODE(workspace.path.parent.stat().st_mode)
    assert mode == 0o700


def test_the_token_is_never_on_disk(tmp_path):
    provider = provider_with_feature(tmp_path)

    workspace = provider.open_workspace("acme/app", "feature-x")

    config = (workspace.path / ".git" / "config").read_text()
    assert TOKEN not in config
    assert "extraheader" not in config
    remote = git(workspace.path, "remote", "get-url", "origin").strip()
    assert remote == (tmp_path / "remotes" / "acme" / "app.git").as_uri()


def test_close_deletes_every_checkout(tmp_path):
    provider = provider_with_feature(tmp_path)
    provider.open_workspace("acme/app", "feature-x")
    provider.open_workspace("acme/app", "main")

    provider.close()

    assert list((tmp_path / "tmp").iterdir()) == []


def test_a_failed_checkout_leaves_no_directory_and_no_token(tmp_path):
    provider = provider_with_feature(tmp_path)

    with pytest.raises(RepoProviderError) as error:
        provider.open_workspace("acme/app", "no-such-branch")

    assert TOKEN not in str(error.value)
    assert list((tmp_path / "tmp").iterdir()) == []


@pytest.mark.parametrize("name", ["-x", "--upload-pack=evil", ""])
def test_a_branch_name_that_git_reads_as_an_option_is_refused(tmp_path, name):
    provider = provider_with_feature(tmp_path)

    with pytest.raises(RepoProviderError):
        provider.open_workspace("acme/app", name)

    assert list((tmp_path / "tmp").iterdir()) == []


def test_each_workspace_is_independent(tmp_path):
    provider = provider_with_feature(tmp_path)
    first = provider.open_workspace("acme/app", "feature-x")
    second = provider.open_workspace("acme/app", "feature-x")

    first.write_file("app.py", "changed\n")

    assert second.read_file("app.py") == "value = 'feature'\n"


def test_commit_makes_the_branch_and_discard_returns_to_the_last_commit(tmp_path):
    provider = provider_with_feature(tmp_path)
    workspace = provider.open_workspace("acme/app", "feature-x")

    workspace.write_file("app.py", "fixed\n")
    workspace.commit("gozu/fix-GR-1", "Fix the bug")
    workspace.write_file("app.py", "half done\n")
    workspace.write_file("scratch.py", "x\n")
    workspace.discard_changes()

    assert workspace.read_file("app.py") == "fixed\n"
    assert workspace.list_files() == ["app.py"]
    assert git(workspace.path, "branch", "--show-current").strip() == "gozu/fix-GR-1"
    assert git(workspace.path, "log", "-1", "--format=%s").strip() == "Fix the bug"


@pytest.mark.parametrize("path", ["../outside.txt", "/etc/veil-test.txt", "a/../../x"])
def test_a_path_outside_the_checkout_is_refused(tmp_path, path):
    provider = provider_with_feature(tmp_path)
    workspace = provider.open_workspace("acme/app", "feature-x")

    with pytest.raises(RepoProviderError):
        workspace.write_file(path, "x")
    with pytest.raises(RepoProviderError):
        workspace.read_file(path)

    assert not (tmp_path / "outside.txt").exists()


def test_a_symlink_that_leaves_the_checkout_is_refused(tmp_path):
    provider = provider_with_feature(tmp_path)
    workspace = provider.open_workspace("acme/app", "feature-x")
    (tmp_path / "secret.txt").write_text("outside\n")
    (workspace.path / "link.txt").symlink_to(tmp_path / "secret.txt")

    with pytest.raises(RepoProviderError):
        workspace.read_file("link.txt")
