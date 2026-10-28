import pytest

from tests.fakes import edit_file, finish
from tests.support.scenario import (
    EDIT_THEN_FINISH,
    FIXED,
    assert_failed_fix,
    make_context,
    toggle_edits,
)
from veil.engine import Settings, run

SMALL_AND_BIG = Settings(step_cap=3, cheap_model="small", strong_model="big")


def test_cheap_attempt_that_hits_the_step_cap_escalates_once_to_the_strong_model(
    tmp_path,
):
    context, _, repos, model = make_context(
        tmp_path,
        {"small": toggle_edits(3), "big": EDIT_THEN_FINISH},
        settings=SMALL_AND_BIG,
    )

    report = run(context)

    assert model.models_used == ["small", "small", "small", "big", "big"]
    assert report.outcomes == {"GR-100": "fixed"}
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED
    assert repos.workspaces_opened == 2


def test_strong_attempt_gets_only_the_failure_reason_of_the_cheap_attempt(tmp_path):
    context, _, _, model = make_context(
        tmp_path,
        {"small": toggle_edits(3), "big": EDIT_THEN_FINISH},
        settings=SMALL_AND_BIG,
    )

    run(context)

    cheap_calls = 3
    strong_start = model.received[cheap_calls]
    assert len(strong_start) == 1
    assert "step cap" in strong_start[0]["content"].lower()
    assert "acme/app" in strong_start[0]["content"]


@pytest.mark.parametrize(
    "cheap_script",
    [
        [[finish("Nothing to do.")]],
        [[edit_file("app.py", "eval(input())", "eval(")], [finish("Edited.")]],
    ],
    ids=["finish-without-a-change", "parse-failure"],
)
def test_other_failures_of_the_cheap_attempt_also_escalate(tmp_path, cheap_script):
    context, _, repos, model = make_context(
        tmp_path,
        {"small": cheap_script, "big": EDIT_THEN_FINISH},
        settings=SMALL_AND_BIG,
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert set(model.models_used) == {"small", "big"}
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED


def test_ticket_file_that_the_engine_cannot_read_does_not_escalate(tmp_path):
    context, tracker, repos, model = make_context(
        tmp_path,
        {"small": [[finish("Done.")]], "big": [[finish("Done.")]]},
        settings=SMALL_AND_BIG,
        file="missing.py",
    )

    report = run(context)

    assert_failed_fix(tracker, repos, report)
    assert model.models_used == []
    assert repos.workspaces_opened == 1


def test_failed_strong_attempt_is_a_failed_fix_with_both_reasons_and_no_third_attempt(
    tmp_path,
):
    context, tracker, repos, model = make_context(
        tmp_path,
        {"small": [[finish("Nothing to do.")]], "big": toggle_edits(3)},
        settings=SMALL_AND_BIG,
    )

    report = run(context)

    comment = assert_failed_fix(tracker, repos, report)
    assert "no change" in comment
    assert "step cap" in comment.lower()
    assert model.models_used == ["small", "big", "big", "big"]
