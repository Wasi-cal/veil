from tests.fakes import finish
from tests.support.scenario import (
    CREDENTIAL,
    GOOD_EDIT,
    assert_failed_fix,
    both_attempts,
    make_context,
)
from veil.engine import run

REASON = "The function parse no longer accepts a string."
EXPLANATION = "Short explanation."
BREAKING = [[GOOD_EDIT], [finish(EXPLANATION, breaking=True, breaking_reason=REASON)]]
NOT_BREAKING = [[GOOD_EDIT], [finish(EXPLANATION)]]


def test_a_breaking_fix_gets_the_label_on_the_ticket_and_on_the_pr(tmp_path):
    context, tracker, repos, _ = make_context(tmp_path, BREAKING)

    run(context)

    assert tracker.labels_on("GR-100") == ["breaking-change"]
    [pr] = repos.pull_requests
    assert pr.labels == ("veil-fix", "breaking-change")


def test_a_breaking_fix_shows_its_reason_first_in_the_pr_and_after_the_link_in_the_comment(
    tmp_path,
):
    context, tracker, repos, _ = make_context(tmp_path, BREAKING)

    run(context)

    [pr] = repos.pull_requests
    section = pr.body.split("\n\n", 1)[1]
    assert section.startswith(f"**Breaking change**\n{REASON}\n\n")
    assert pr.body.index("Breaking change") < pr.body.index("Why this is a problem")
    [comment] = tracker.comments_on("GR-100")
    lines = comment.splitlines()
    assert lines[0] == f"The Engine opened a Fix PR: {pr.url}"
    assert lines[1] == f"Breaking change: {REASON}"


def test_a_breaking_fix_is_in_the_run_report(tmp_path):
    context, _, _, _ = make_context(tmp_path, BREAKING)

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert report.breaking == {"GR-100": REASON}


def test_a_fix_that_is_not_breaking_gets_no_label_and_no_extra_text(tmp_path):
    context, tracker, repos, _ = make_context(tmp_path, NOT_BREAKING)

    report = run(context)

    assert tracker.labels_on("GR-100") == []
    [pr] = repos.pull_requests
    assert pr.labels == ("veil-fix",)
    assert "Breaking change" not in pr.body
    assert all("Breaking change" not in c for c in tracker.comments_on("GR-100"))
    assert report.breaking == {}


def test_a_failed_fix_gets_no_breaking_label(tmp_path):
    bad = finish(
        EXPLANATION,
        breaking=True,
        breaking_reason=f"The value {CREDENTIAL} is gone.",
    )
    context, tracker, repos, _ = make_context(
        tmp_path,
        both_attempts([[GOOD_EDIT], [bad]]),
        credentials=(CREDENTIAL,),
    )

    report = run(context)

    assert_failed_fix(tracker, repos, report)
    assert report.breaking == {}


def test_a_label_that_a_person_removes_does_not_come_back_on_a_later_run(tmp_path):
    context, tracker, repos, _ = make_context(tmp_path, BREAKING)
    run(context)
    tracker.remove_label("GR-100", "breaking-change")

    second = run(context)

    assert second.outcomes == {"GR-100": "skipped"}
    assert tracker.labels_on("GR-100") == []
    assert len(repos.pull_requests) == 1
