import pytest

from tests.engine.support import (
    EDIT_THEN_FINISH,
    FIXED,
    GOOD_EDIT,
    VULNERABLE,
    assert_failed_fix,
    make_context,
    toggle_edits,
)
from tests.fakes import edit_file, finish, search
from veil.engine import Settings, ToolCall, run


def test_finish_without_any_edit_is_a_failed_fix(tmp_path):
    context, tracker, repos, _ = make_context(tmp_path, [[finish("Nothing to do.")]])

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


@pytest.mark.parametrize(
    "bad_call",
    [
        ToolCall(name="delete_everything", arguments={}),
        ToolCall(name="edit_file", arguments={"path": "app.py"}),
        ToolCall(
            name="edit_file",
            arguments={"path": "app.py", "old": "a", "new": "b", "x": 1},
        ),
        ToolCall(name="read_file", arguments={}),
        ToolCall(name="read_file", arguments={"path": "app.py", "start_line": 0}),
        ToolCall(name="read_file", arguments={"path": "app.py", "start_line": "one"}),
        ToolCall(name="read_file", arguments={"path": "nope.py"}),
        ToolCall(name="search", arguments={"pattern": "("}),
        ToolCall(name="read_file", arguments={"path": ""}),
        ToolCall(name="read_file", arguments={"path": "."}),
        ToolCall(name="edit_file", arguments={"path": "", "old": "a", "new": "b"}),
        ToolCall(name="list_dir", arguments={"path": "../.."}),
    ],
    ids=[
        "unknown-tool",
        "missing-arguments",
        "extra-arguments",
        "read-without-path",
        "start-line-zero",
        "start-line-not-a-number",
        "read-missing-file",
        "bad-regex",
        "read-empty-path",
        "read-dot",
        "edit-empty-path",
        "list-outside-repo",
    ],
)
def test_bad_tool_call_gives_the_model_an_error_and_the_run_goes_on(tmp_path, bad_call):
    context, _, repos, _ = make_context(
        tmp_path, [[bad_call], *EDIT_THEN_FINISH.copy()]
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert len(repos.pull_requests) == 1


def test_failed_fix_does_not_stop_the_next_ticket(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path,
        [*toggle_edits(3), *EDIT_THEN_FINISH],
        settings=Settings(step_cap=3),
        extra_tickets=[{"key": "GR-101"}],
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "failed", "GR-101": "fixed"}
    assert len(repos.pull_requests) == 1
    assert tracker.labels_on("GR-101") == []
    assert tracker.status_of("GR-101") == "In Review"


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


def test_model_reply_with_no_tool_calls_counts_as_a_step(tmp_path):
    context, tracker, repos, _ = make_context(
        tmp_path, [[]] * 5, settings=Settings(step_cap=3)
    )

    report = run(context)

    assert_failed_fix(tracker, repos, report)


def test_calls_after_finish_in_the_same_reply_are_ignored(tmp_path):
    context, _, repos, _ = make_context(
        tmp_path,
        [[GOOD_EDIT, finish("Done."), edit_file("app.py", "import os", "import sys")]],
    )

    run(context)

    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED


def test_binary_file_does_not_break_search(tmp_path):
    context, _, _, _ = make_context(
        tmp_path,
        [[search("value")], *EDIT_THEN_FINISH],
        files={"app.py": VULNERABLE, "blob.bin": b"\xff\xfe\x00value"},
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
