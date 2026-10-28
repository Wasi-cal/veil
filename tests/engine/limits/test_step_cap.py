from tests.support.scenario import (
    EDIT_THEN_FINISH,
    assert_failed_fix,
    both_attempts,
    make_context,
    toggle_edits,
)
from veil.engine import Settings, run


def test_attempt_that_reaches_the_step_cap_is_a_failed_fix(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path, both_attempts(toggle_edits(3)), settings=Settings(step_cap=3)
    )

    report = run(context)

    comment = assert_failed_fix(tracker, repos, report)
    assert "step" in comment.lower()


def test_attempt_that_finishes_on_the_last_allowed_step_is_fixed(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path, EDIT_THEN_FINISH, settings=Settings(step_cap=2)
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert len(repos.pull_requests) == 1
    assert tracker.labels_on("GR-100") == []


def test_model_reply_with_no_tool_calls_counts_as_a_step(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path, both_attempts([[]] * 3), settings=Settings(step_cap=3)
    )

    report = run(context)

    assert_failed_fix(tracker, repos, report)
