import pytest

from tests.fakes import search
from tests.support.scenario import (
    EDIT_THEN_FINISH,
    VULNERABLE,
    make_context,
)
from veil.engine import ToolCall, run


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


def test_binary_file_does_not_break_search(tmp_path):
    context, _, _, _ = make_context(
        tmp_path,
        [[search("value")], *EDIT_THEN_FINISH],
        files={"app.py": VULNERABLE, "blob.bin": b"\xff\xfe\x00value"},
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
