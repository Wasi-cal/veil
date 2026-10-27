import pytest
from pydantic import ValidationError

from tests.fakes import edit_file, finish
from tests.support.scenario import (
    assert_failed_fix,
    make_context,
)
from veil.engine import Settings, run


def numbered(count, value):
    return "".join(f"line {n} {value}\n" for n in range(count))


def test_default_step_cap_is_25_tool_calls(tmp_path):
    flips = [(f"value = {n}", f"value = {n + 1}") for n in range(24)]
    script = [[edit_file("app.py", *pair)] for pair in flips]

    context, _, repos, _ = make_context(
        tmp_path, [*script, [finish("Done.")]], files={"app.py": "value = 0\n"}
    )
    assert run(context).outcomes == {"GR-100": "fixed"}
    assert len(repos.pull_requests) == 1

    context, tracker, repos, _ = make_context(
        tmp_path / "over",
        [*script, [edit_file("app.py", "value = 24", "value = 25")], [finish("Done.")]],
        files={"app.py": "value = 0\n"},
    )
    assert_failed_fix(tracker, repos, run(context))


@pytest.mark.parametrize(("lines", "outcome"), [(200, "fixed"), (201, "failed")])
def test_default_diff_limit_is_200_changed_lines(tmp_path, lines, outcome):
    """Replacing N lines changes N lines, so 200 lines is exactly the limit."""
    context, _, _, _ = make_context(
        tmp_path,
        [
            [edit_file("data.txt", numbered(lines, "a"), numbered(lines, "b"))],
            [finish("Done.")],
        ],
        files={"data.txt": numbered(lines, "a")},
        file="data.txt",
        line=1,
    )

    report = run(context)

    assert report.outcomes == {"GR-100": outcome}


@pytest.mark.parametrize(
    "setting",
    [
        "allow_workflow_edits",
        "allow_new_files",
        "allow_deletions",
        "allow_default_branch",
    ],
)
def test_safety_rules_are_not_settings(setting):
    with pytest.raises(ValidationError):
        Settings(**{setting: True})


@pytest.mark.parametrize(
    "bad",
    [
        {"step_cap": 0},
        {"step_cap": -1},
        {"diff_limit": -1},
        {"tool_result_max_bytes": 0},
        {"read_file_max_lines": 0},
        {"search_max_matches": 0},
    ],
)
def test_settings_reject_nonsense_limits(bad):
    with pytest.raises(ValidationError):
        Settings(**bad)
