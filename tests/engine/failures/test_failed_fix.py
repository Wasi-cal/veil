import pytest

from tests.fakes import finish
from tests.support.scenario import (
    EDIT_THEN_FINISH,
    assert_failed_fix,
    both_attempts,
    make_context,
    toggle_edits,
)
from veil.engine import Settings, run


def test_finish_without_any_edit_is_a_failed_fix(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path, both_attempts([[finish("Nothing to do.")]])
    )

    report = run(context)

    comment = assert_failed_fix(tracker, repos, report)
    assert "change" in comment.lower()


def test_ticket_file_that_is_not_in_the_repo_is_a_failed_fix(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path, [[finish("Done.")]], file="missing.py"
    )

    report = run(context)

    comment = assert_failed_fix(tracker, repos, report)
    assert "missing.py" in comment


@pytest.mark.parametrize("file", [".env", "../outside.py", "keys/server.pem"])
def test_ticket_that_points_at_a_secret_or_outside_file_is_a_failed_fix_and_nothing_is_read(
    tmp_path, file
):
    context, tracker, repos, model = make_context(
        tmp_path,
        [[finish("Done.")]],
        files={"app.py": "x = 1\n", ".env": "KEY=1\n", "keys/server.pem": "PEM\n"},
        file=file,
        line=1,
    )

    report = run(context)

    assert_failed_fix(tracker, repos, report)
    assert model.received == []


def test_failed_fix_does_not_stop_the_next_ticket(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path,
        {
            "cheap-model": [*toggle_edits(3), *EDIT_THEN_FINISH],
            "strong-model": toggle_edits(3),
        },
        settings=Settings(step_cap=3),
        extra_tickets=[{"key": "GR-101"}],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "failed", "GR-101": "fixed"}
    assert len(repos.pull_requests) == 1
    assert tracker.labels_on("GR-101") == []
    assert tracker.status_of("GR-101") == "In Review"


def test_a_failed_comment_write_does_not_make_the_next_run_try_the_ticket_again(
    tmp_path,
):
    context, tracker, repos, model = make_context(
        tmp_path, both_attempts([[finish("Nothing to do.")]])
    )
    tracker.explode_on_next_comment()
    with pytest.raises(RuntimeError):
        run(context)
    calls_after_first_run = len(model.models_used)

    report = run(context)

    assert report.skipped == {"failed_fix": ["GR-100"]}
    assert len(model.models_used) == calls_after_first_run
    assert repos.pull_requests == []
