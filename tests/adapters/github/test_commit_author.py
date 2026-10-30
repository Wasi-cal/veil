from pydantic import SecretStr

from tests.adapters.github.support import TOKEN, git, make_remote
from veil.adapters.github.models.commit_author import CommitAuthor
from veil.adapters.github.provider import GitHubRepoProvider

BOT = CommitAuthor(
    name="gozu-veil[bot]", email="9001+gozu-veil[bot]@users.noreply.github.com"
)


def provider(tmp_path, **extra):
    make_remote(tmp_path)
    (tmp_path / "tmp").mkdir()
    return GitHubRepoProvider(
        token=SecretStr(TOKEN),
        api=None,
        remote_url=lambda repo: (tmp_path / "remotes" / f"{repo}.git").as_uri(),
        branch_prefix="gozu/fix-",
        temp_root=tmp_path / "tmp",
        **extra,
    )


def last_commit_identity(workspace):
    return git(workspace.path, "log", "-1", "--format=%an|%ae|%cn|%ce").strip()


def test_a_commit_carries_the_given_author_as_author_and_committer(tmp_path):
    workspace = provider(tmp_path, author=BOT).open_workspace("acme/app", "main")
    workspace.write_file("app.py", "value = 'fixed'\n")

    workspace.commit("gozu/fix-1", "Fix it")

    assert last_commit_identity(workspace) == (
        "gozu-veil[bot]|9001+gozu-veil[bot]@users.noreply.github.com"
        "|gozu-veil[bot]|9001+gozu-veil[bot]@users.noreply.github.com"
    )


def test_a_commit_without_a_given_author_keeps_the_default_identity(tmp_path):
    workspace = provider(tmp_path).open_workspace("acme/app", "main")
    workspace.write_file("app.py", "value = 'fixed'\n")

    workspace.commit("gozu/fix-1", "Fix it")

    assert last_commit_identity(workspace) == (
        "Gozu Veil|veil@gozu.invalid|Gozu Veil|veil@gozu.invalid"
    )
