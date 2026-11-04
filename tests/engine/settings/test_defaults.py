import pytest
from pydantic import ValidationError

from tests.fakes import edit_file, finish
from tests.support.scenario import (
    assert_failed_fix,
    both_attempts,
    make_context,
)
from veil.engine import Settings, run


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
        both_attempts(
            [
                *script,
                [edit_file("app.py", "value = 24", "value = 25")],
                [finish("Done.")],
            ]
        ),
        files={"app.py": "value = 0\n"},
    )
    assert_failed_fix(tracker, repos, run(context))


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
        Settings.model_validate({setting: True})


@pytest.mark.parametrize(
    "bad",
    [
        {"step_cap": 0},
        {"step_cap": -1},
        {"tool_result_max_bytes": 0},
        {"read_file_max_lines": 0},
        {"search_max_matches": 0},
        {"ticket_token_cap": 0},
        {"cheap_model": ""},
        {"strong_model": ""},
    ],
)
def test_settings_reject_nonsense_limits(bad):
    with pytest.raises(ValidationError):
        Settings(**bad)


def test_default_ticket_token_cap_is_100_000():
    assert Settings().ticket_token_cap == 100_000
