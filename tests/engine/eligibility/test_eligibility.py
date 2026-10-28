from tests.fakes import finish
from tests.support.scenario import (
    EDIT_THEN_FINISH,
    assert_untouched,
    both_attempts,
    make_context,
)
from veil.engine import Settings, run


def test_ticket_raised_against_a_fix_branch_is_skipped(tmp_path):
    context, tracker, repos, model = make_context(
        tmp_path, EDIT_THEN_FINISH, branch="gozu/fix-gr-7"
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "skipped"}
    assert report.skipped == {"raised_against_fix_branch": ["GR-100"]}
    assert_untouched(tracker, repos, model)


def test_ticket_with_an_open_pr_is_skipped(tmp_path):
    context, tracker, repos, model = make_context(tmp_path, EDIT_THEN_FINISH)
    repos.seed_pull_request("acme/app", "gozu/fix-earlier", labels=("issue-gr-100",))

    report = run(context)

    assert report.outcomes == {"GR-100": "skipped"}
    assert report.skipped == {"open_pr": ["GR-100"]}
    assert_untouched(tracker, repos, model)


def test_ticket_with_a_fix_branch_that_carries_its_label_is_skipped(tmp_path):
    context, tracker, repos, model = make_context(tmp_path, EDIT_THEN_FINISH)
    repos.seed_branch("acme/app", "gozu/fix-closed-pr", labels=("issue-gr-100",))

    report = run(context)

    assert report.skipped == {"fix_branch": ["GR-100"]}
    assert_untouched(tracker, repos, model)


def test_a_fix_for_another_ticket_does_not_block_this_ticket(tmp_path):
    context, _, repos, _ = make_context(tmp_path, EDIT_THEN_FINISH)
    repos.seed_pull_request("acme/app", "gozu/fix-other", labels=("issue-gr-999",))
    repos.seed_pull_request(
        "acme/other-repo", "gozu/fix-same", labels=("issue-gr-100",)
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert report.skipped == {}


def test_ticket_with_the_failed_fix_marker_is_skipped_until_a_human_removes_it(
    tmp_path,
):
    context, tracker, repos, model = make_context(
        tmp_path, EDIT_THEN_FINISH, labels=("issue-gr-100", "veil-failed-fix")
    )

    report = run(context)

    assert report.skipped == {"failed_fix": ["GR-100"]}
    assert_untouched(tracker, repos, model)


def test_ticket_with_no_issue_label_is_skipped_because_a_duplicate_cannot_be_ruled_out(
    tmp_path,
):
    context, tracker, repos, model = make_context(
        tmp_path, EDIT_THEN_FINISH, labels=("security",)
    )

    report = run(context)

    assert report.skipped == {"no_issue_label": ["GR-100"]}
    assert_untouched(tracker, repos, model)


def test_second_run_after_a_full_run_creates_nothing_new(tmp_path):
    context, tracker, repos, model = make_context(tmp_path, EDIT_THEN_FINISH)
    run(context)
    calls_after_first_run = len(model.models_used)

    report = run(context)

    assert report.outcomes == {"GR-100": "skipped"}
    assert report.skipped == {"open_pr": ["GR-100"]}
    assert len(repos.pull_requests) == 1
    assert repos.workspaces_opened == 1
    assert len(model.models_used) == calls_after_first_run
    assert len(tracker.comments_on("GR-100")) == 1


def test_second_run_after_a_partial_run_fixes_only_the_tickets_that_were_left(
    tmp_path,
):
    context, tracker, repos, _ = make_context(
        tmp_path,
        [*EDIT_THEN_FINISH, *EDIT_THEN_FINISH],
        tokens_per_call=300,
        settings=Settings(token_ceiling=500),
        extra_tickets=[{"key": "GR-101"}],
    )

    first = run(context)
    second = run(context)

    assert first.outcomes == {"GR-100": "fixed", "GR-101": "left_for_next_run"}
    assert second.outcomes == {"GR-100": "skipped", "GR-101": "fixed"}
    assert len(repos.pull_requests) == 2
    assert repos.workspaces_opened == 2
    assert len(tracker.comments_on("GR-100")) == 1
    assert len(tracker.comments_on("GR-101")) == 1


def test_second_run_does_not_retry_or_comment_again_on_a_failed_fix(tmp_path):
    context, tracker, repos, model = make_context(
        tmp_path, both_attempts([[finish("Nothing to do.")]])
    )
    run(context)
    calls_after_first_run = len(model.models_used)

    report = run(context)

    assert report.skipped == {"failed_fix": ["GR-100"]}
    assert len(model.models_used) == calls_after_first_run
    assert len(tracker.comments_on("GR-100")) == 1
    assert tracker.labels_on("GR-100") == ["veil-failed-fix"]
    assert repos.pull_requests == []


def test_report_counts_the_skipped_tickets_by_reason_and_still_fixes_the_rest(tmp_path):
    context, _, repos, _ = make_context(
        tmp_path,
        EDIT_THEN_FINISH,
        branch="gozu/fix-gr-7",
        extra_tickets=[
            {"key": "GR-101", "branch": "main"},
            {"key": "GR-102", "branch": "main"},
            {"key": "GR-103", "branch": "main", "labels": ("security",)},
            {"key": "GR-104", "branch": "gozu/fix-gr-8"},
            {"key": "GR-105", "branch": "main"},
        ],
    )
    repos.seed_pull_request("acme/app", "gozu/fix-101", labels=("issue-gr-101",))
    repos.seed_pull_request("acme/app", "gozu/fix-102", labels=("issue-gr-102",))

    report = run(context)

    assert report.skipped == {
        "raised_against_fix_branch": ["GR-100", "GR-104"],
        "open_pr": ["GR-101", "GR-102"],
        "no_issue_label": ["GR-103"],
    }
    assert report.outcomes["GR-105"] == "fixed"
    assert sum(1 for o in report.outcomes.values() if o == "skipped") == 5
    assert len(repos.pull_requests) == 1
    assert repos.workspaces_opened == 1


def test_second_ticket_with_the_same_issue_label_is_skipped_in_the_same_run(tmp_path):
    context, _, repos, _ = make_context(
        tmp_path,
        [*EDIT_THEN_FINISH, *EDIT_THEN_FINISH],
        labels=("issue-same",),
        extra_tickets=[{"key": "GR-101", "labels": ("issue-same",)}],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed", "GR-101": "skipped"}
    assert report.skipped == {"duplicate_issue": ["GR-101"]}
    assert len(repos.pull_requests) == 1


def test_a_ticket_that_the_tracker_lists_twice_is_fixed_once(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path,
        [*EDIT_THEN_FINISH, *EDIT_THEN_FINISH],
        extra_tickets=[{"key": "GR-100"}],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert report.skipped == {}
    assert len(repos.pull_requests) == 1
    assert len(tracker.comments_on("GR-100")) == 1
