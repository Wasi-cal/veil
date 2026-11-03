import pytest

from tests.adapters.github.support import TOKEN, git, make_provider, make_remote
from tests.fakes.github_api import StubGitHubApi
from veil.engine import NewPr
from veil.engine.errors.repo_provider_error import RepoProviderError

FIX_BRANCH = "gozu/fix-GR-1"


def remote_branch_heads(tmp_path) -> dict[str, str]:
    bare = tmp_path / "remotes" / "acme" / "app.git"
    out = git(bare, "for-each-ref", "--format=%(refname:short) %(objectname)")
    return dict(line.split() for line in out.splitlines())


def new_pr(**fields) -> NewPr:
    base = {
        "repo": "acme/app",
        "head": FIX_BRANCH,
        "base": "feature-x",
        "title": "Fix GR-1",
        "body": "Replaced eval with int.",
        "labels": ("issue-abc123",),
    }
    return NewPr(**{**base, **fields})


def committed_fix(tmp_path):
    """A provider with a Fix commit on the Fix branch. The Fix commit is not pushed yet."""
    make_remote(tmp_path, branches={"feature-x": {"app.py": "value = 'feature'\n"}})
    api = StubGitHubApi()
    provider = make_provider(tmp_path, api=api)
    workspace = provider.open_workspace("acme/app", "feature-x")
    workspace.write_file("app.py", "fixed\n")
    workspace.commit(FIX_BRANCH, "Fix the bug")
    return provider, api


def test_the_pr_has_the_fix_branch_and_targets_the_source_branch(tmp_path):
    provider, api = committed_fix(tmp_path)

    url = provider.open_pr(new_pr())

    [pr] = api.created
    assert url == pr.url
    assert (pr.head_branch, pr.base_branch, pr.draft) == (
        FIX_BRANCH,
        "feature-x",
        False,
    )
    assert (pr.title, pr.body, pr.labels) == (
        "Fix GR-1",
        "Replaced eval with int.",
        ("issue-abc123",),
    )
    bare = tmp_path / "remotes" / "acme" / "app.git"
    assert git(bare, "show", f"{FIX_BRANCH}:app.py") == "fixed\n"


def test_only_the_fix_branch_changes_in_the_remote(tmp_path):
    provider, _ = committed_fix(tmp_path)
    before = remote_branch_heads(tmp_path)

    provider.open_pr(new_pr())

    after = remote_branch_heads(tmp_path)
    assert {k: v for k, v in after.items() if k != FIX_BRANCH} == before
    assert FIX_BRANCH in after


def test_a_second_call_for_the_same_branch_returns_the_first_url(tmp_path):
    provider, api = committed_fix(tmp_path)

    first = provider.open_pr(new_pr())
    second = provider.open_pr(new_pr())

    assert second == first
    assert len(api.created) == 1


@pytest.mark.parametrize(
    "fields",
    [
        {"head": "feature-x"},
        {"head": "main", "base": "feature-x"},
        {"head": FIX_BRANCH, "base": FIX_BRANCH},
        {"head": "-x"},
    ],
    ids=["source branch", "default branch", "head is base", "option-like"],
)
def test_the_provider_refuses_to_push_any_other_branch(tmp_path, fields):
    provider, api = committed_fix(tmp_path)
    before = remote_branch_heads(tmp_path)

    with pytest.raises(RepoProviderError):
        provider.open_pr(new_pr(**fields))

    assert remote_branch_heads(tmp_path) == before
    assert api.created == []


def test_a_branch_that_no_checkout_holds_cannot_be_pushed(tmp_path):
    provider, api = committed_fix(tmp_path)

    with pytest.raises(RepoProviderError) as error:
        provider.open_pr(new_pr(head="gozu/fix-GR-99"))

    assert TOKEN not in str(error.value)
    assert api.created == []


def test_a_pr_against_the_default_branch_is_refused_and_nothing_is_pushed(tmp_path):
    make_remote(tmp_path, branches={"feature-x": {"app.py": "value = 'feature'\n"}})
    api = StubGitHubApi(default_branch="feature-x")
    provider = make_provider(tmp_path, api=api)
    workspace = provider.open_workspace("acme/app", "feature-x")
    workspace.write_file("app.py", "fixed\n")
    workspace.commit(FIX_BRANCH, "Fix the bug")
    before = remote_branch_heads(tmp_path)

    with pytest.raises(RepoProviderError, match="default branch"):
        provider.open_pr(new_pr())

    assert remote_branch_heads(tmp_path) == before
    assert api.created == []


def test_a_fix_branch_that_is_the_default_branch_is_refused(tmp_path):
    provider, api = committed_fix(tmp_path)
    api._default_branch = FIX_BRANCH

    with pytest.raises(RepoProviderError, match="default branch"):
        provider.open_pr(new_pr())

    assert api.created == []


def test_the_default_branch_is_asked_once_for_each_repo(tmp_path):
    provider, api = committed_fix(tmp_path)

    provider.open_pr(new_pr())
    provider.open_pr(new_pr())

    assert api.default_branch_questions == 1
