import pytest

from tests.adapters.github.support import make_provider, make_remote
from tests.fakes.github_api import StubGitHubApi
from veil.adapters.github.models.pull_request import PullRequest
from veil.engine import FixQuery

LABEL = "issue-abc123"
FIX_BRANCH = "veil/fix-GR-5"


def pr(**fields) -> PullRequest:
    base = {
        "url": "https://github.example.invalid/acme/app/pull/1",
        "base_repo": "acme/app",
        "head_repo": "acme/app",
        "head_branch": "feature-x",
        "base_branch": "main",
        "state": "open",
        "labels": (),
        "title": "t",
        "body": "b",
        "draft": False,
    }
    return PullRequest(**{**base, **fields})


def provider_with(tmp_path, pull_requests):
    make_remote(
        tmp_path,
        branches={"feature-x": {"app.py": "x\n"}, FIX_BRANCH: {"app.py": "y\n"}},
    )
    return make_provider(tmp_path, api=StubGitHubApi(pull_requests))


def query(**fields) -> FixQuery:
    base = {
        "repo": "acme/app",
        "issue_label": LABEL,
        "source_branch": "feature-x",
        "branch_prefix": "veil/fix-",
        "ticket_key": "GR-5",
    }
    return FixQuery(**{**base, **fields})


def test_an_open_pr_with_this_head_is_a_source_pr(tmp_path):
    provider = provider_with(tmp_path, [pr()])

    assert provider.has_open_pr("acme/app", "feature-x") is True


@pytest.mark.parametrize(
    "fields",
    [{"state": "closed"}, {"state": "merged"}, {"head_repo": "fork/app"}],
    ids=["closed", "merged", "from a fork"],
)
def test_a_pr_that_is_not_open_or_not_from_this_repo_is_not_a_source_pr(
    tmp_path, fields
):
    provider = provider_with(tmp_path, [pr(**fields)])

    assert provider.has_open_pr("acme/app", "feature-x") is False


def test_a_branch_without_a_pr_is_not_a_source_pr(tmp_path):
    provider = provider_with(tmp_path, [pr(head_branch="other")])

    assert provider.has_open_pr("acme/app", "feature-x") is False


def test_an_open_fix_pr_on_the_source_branch_is_an_open_pr(tmp_path):
    fix = pr(head_branch=FIX_BRANCH, base_branch="feature-x", labels=(LABEL,))
    provider = provider_with(tmp_path, [fix])

    assert provider.find_existing_fix(query()) == "open_pr"


@pytest.mark.parametrize(
    "fields",
    [
        {"base_branch": "main"},
        {"labels": ("issue-other",)},
        {"head_repo": "fork/app"},
        {"state": "merged", "base_branch": "main"},
        {"state": "merged", "labels": ("issue-other",)},
        {"state": "merged", "head_repo": "fork/app"},
        {"state": "merged", "head_branch": "feature-x"},
    ],
    ids=[
        "other base",
        "other label",
        "from a fork",
        "merged, other base",
        "merged, other label",
        "merged, from a fork",
        "merged, not a Fix branch",
    ],
)
def test_a_pr_that_does_not_match_is_not_an_existing_fix(tmp_path, fields):
    base = {"head_branch": FIX_BRANCH, "base_branch": "feature-x", "labels": (LABEL,)}
    provider = provider_with(tmp_path, [pr(**{**base, **fields})])

    assert provider.find_existing_fix(query()) is None


def test_a_merged_fix_pr_on_the_source_branch_is_a_merged_pr(tmp_path):
    fix = pr(
        head_branch=FIX_BRANCH,
        base_branch="feature-x",
        labels=(LABEL,),
        state="merged",
    )
    provider = provider_with(tmp_path, [fix])

    assert provider.find_existing_fix(query()) == "merged_pr"


def test_a_merged_fix_pr_is_found_even_if_its_branch_is_deleted(tmp_path):
    fix = pr(
        head_branch="veil/fix-GR-9",
        base_branch="feature-x",
        labels=(LABEL,),
        state="merged",
    )
    provider = provider_with(tmp_path, [fix])

    assert provider.find_existing_fix(query()) == "merged_pr"


def test_an_open_pr_wins_over_a_merged_pr(tmp_path):
    merged = pr(
        head_branch=FIX_BRANCH, base_branch="feature-x", labels=(LABEL,), state="merged"
    )
    opened = pr(head_branch="veil/fix-GR-7", base_branch="feature-x", labels=(LABEL,))
    provider = provider_with(tmp_path, [merged, opened])

    assert provider.find_existing_fix(query()) == "open_pr"


def test_a_merged_pr_wins_over_a_fix_branch(tmp_path):
    merged = pr(
        head_branch="veil/fix-GR-9",
        base_branch="feature-x",
        labels=(LABEL,),
        state="merged",
    )
    closed = pr(
        head_branch=FIX_BRANCH, base_branch="feature-x", labels=(LABEL,), state="closed"
    )
    provider = provider_with(tmp_path, [closed, merged])

    assert provider.find_existing_fix(query()) == "merged_pr"


def test_a_closed_fix_pr_whose_branch_still_exists_is_a_fix_branch(tmp_path):
    fix = pr(
        head_branch=FIX_BRANCH, base_branch="feature-x", labels=(LABEL,), state="closed"
    )
    provider = provider_with(tmp_path, [fix])

    assert provider.find_existing_fix(query()) == "fix_branch"


def test_a_closed_fix_pr_whose_branch_is_gone_is_not_a_fix(tmp_path):
    fix = pr(
        head_branch="veil/fix-GR-9",
        base_branch="feature-x",
        labels=(LABEL,),
        state="closed",
    )
    provider = provider_with(tmp_path, [fix])

    assert provider.find_existing_fix(query()) is None


def test_a_closed_pr_without_the_branch_prefix_is_not_a_fix_branch(tmp_path):
    other = pr(head_branch="feature-x", labels=(LABEL,), state="closed")
    provider = provider_with(tmp_path, [other])

    assert provider.find_existing_fix(query()) is None


def test_an_open_pr_wins_over_a_fix_branch(tmp_path):
    closed = pr(
        head_branch=FIX_BRANCH, base_branch="feature-x", labels=(LABEL,), state="closed"
    )
    opened = pr(head_branch="veil/fix-GR-7", base_branch="feature-x", labels=(LABEL,))
    provider = provider_with(tmp_path, [closed, opened])

    assert provider.find_existing_fix(query()) == "open_pr"


def test_the_repository_name_is_compared_without_case(tmp_path):
    provider = provider_with(tmp_path, [pr(head_repo="Acme/App")])

    assert provider.has_open_pr("acme/app", "feature-x") is True


def test_a_merged_fix_pr_under_the_older_gozu_prefix_is_still_found(tmp_path):
    fix = pr(
        head_branch="gozu/fix-GR-9",
        base_branch="feature-x",
        labels=(LABEL,),
        state="merged",
    )
    provider = provider_with(tmp_path, [fix])

    assert provider.find_existing_fix(query()) == "merged_pr"


def veil_pr(key="GR-5", **fields):
    body = f"## {key} · `app.py:3`\n\n**Why this is a problem**\nIt is unsafe."
    return pr(
        head_branch=FIX_BRANCH,
        base_branch="feature-x",
        labels=("veil-fix",),
        body=body,
        **fields,
    )


def test_an_open_pr_with_the_veil_fix_label_and_the_ticket_section_is_found(tmp_path):
    provider = provider_with(tmp_path, [veil_pr()])

    assert provider.find_existing_fix(query()) == "open_pr"


def test_a_veil_fix_pr_of_another_ticket_is_not_found(tmp_path):
    provider = provider_with(tmp_path, [veil_pr(key="GR-6")])

    assert provider.find_existing_fix(query()) is None


def test_a_pr_with_the_ticket_section_but_no_veil_fix_label_is_not_found(tmp_path):
    other = pr(
        head_branch="other", base_branch="feature-x", body="## GR-5 · `app.py:3`\n"
    )
    provider = provider_with(tmp_path, [other])

    assert provider.find_existing_fix(query()) is None


def test_a_merged_veil_fix_pr_is_found_by_its_ticket_section(tmp_path):
    provider = provider_with(tmp_path, [veil_pr(state="merged")])

    assert provider.find_existing_fix(query()) == "merged_pr"


def test_a_shared_veil_fix_pr_is_found_for_each_ticket_in_it(tmp_path):
    body = "## GR-5 · `a.py:1`\n\ntext\n\n## GR-6 · `a.py:9`\n\ntext"
    shared = pr(
        head_branch=FIX_BRANCH, base_branch="feature-x", labels=("veil-fix",), body=body
    )
    provider = provider_with(tmp_path, [shared])

    assert provider.find_existing_fix(query(ticket_key="GR-6")) == "open_pr"


def test_many_questions_about_one_repo_read_the_pull_requests_once(tmp_path):
    api = StubGitHubApi([veil_pr()])
    make_remote(
        tmp_path,
        branches={"feature-x": {"app.py": "x\n"}, FIX_BRANCH: {"app.py": "y\n"}},
    )
    provider = make_provider(tmp_path, api=api)

    for key in ("GR-5", "GR-6", "GR-7"):
        provider.find_existing_fix(query(ticket_key=key))
        provider.has_open_pr("acme/app", "feature-x")

    assert api.pull_request_reads == 1
