import pytest

from tests.support.scenario import (
    EDIT_THEN_FINISH,
    FIXED,
    VULNERABLE,
    assert_untouched,
    make_context,
    toggle_edits,
)
from veil.engine import Settings, run

MAIN_WITHOUT_THE_BUG = {"app.py": "x = 1\n"}
BRANCH_WITH_THE_BUG = {"app.py": VULNERABLE}


def source_pr_context(tmp_path):
    """A ticket on the open Source PR feature-x. The bug is on that branch and not on main."""
    return make_context(
        tmp_path,
        EDIT_THEN_FINISH,
        files=MAIN_WITHOUT_THE_BUG,
        source_files=BRANCH_WITH_THE_BUG,
        branch="feature-x",
    )


def test_the_fix_is_built_from_the_branch_of_the_source_pr(tmp_path):
    context, _, repos, _ = source_pr_context(tmp_path)

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED


def test_the_fix_pr_targets_the_branch_of_the_source_pr(tmp_path):
    context, _, repos, _ = source_pr_context(tmp_path)

    run(context)

    [pr] = repos.pull_requests
    assert pr.base == "feature-x"
    assert pr.draft is True
    assert repos.commit_count_on(pr) == 1


def test_the_engine_never_moves_the_source_branch_or_main(tmp_path):
    context, _, repos, _ = source_pr_context(tmp_path)
    source_before = repos.head_of("acme/app", "feature-x")
    main_before = repos.head_of("acme/app", "main")

    run(context)

    [pr] = repos.pull_requests
    assert pr.head.startswith("gozu/fix-")
    assert pr.head != pr.base
    assert repos.head_of("acme/app", "feature-x") == source_before
    assert repos.head_of("acme/app", "main") == main_before
    assert repos.head_of("acme/app", pr.head)


@pytest.mark.parametrize(
    "branch",
    ["feature-x", "main"],
    ids=["pr-merged-or-closed", "scan-of-the-default-branch"],
)
def test_ticket_whose_source_pr_is_not_open_is_skipped(tmp_path, branch):
    context, tracker, repos, model = make_context(
        tmp_path, EDIT_THEN_FINISH, branch=branch, open_source_pr=False
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "skipped"}
    assert report.skipped == {"source_pr_not_open": ["GR-100"]}
    assert_untouched(tracker, repos, model)


def test_the_strong_attempt_also_starts_on_a_fresh_checkout_of_the_source_branch(
    tmp_path,
):
    context, _, repos, _ = make_context(
        tmp_path,
        {"small": toggle_edits(3), "big": EDIT_THEN_FINISH},
        settings=Settings(step_cap=3, cheap_model="small", strong_model="big"),
        files=MAIN_WITHOUT_THE_BUG,
        source_files=BRANCH_WITH_THE_BUG,
        branch="feature-x",
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert repos.workspaces_opened == 2
    [pr] = repos.pull_requests
    assert pr.base == "feature-x"
    assert repos.file_on(pr, "app.py") == FIXED


def test_a_second_run_makes_no_duplicates_in_the_source_pr_flow(tmp_path):
    context, tracker, repos, _ = source_pr_context(tmp_path)
    run(context)

    report = run(context)

    assert report.skipped == {"open_pr": ["GR-100"]}
    assert len(repos.pull_requests) == 1
    assert repos.workspaces_opened == 1
    assert len(tracker.comments_on("GR-100")) == 1
