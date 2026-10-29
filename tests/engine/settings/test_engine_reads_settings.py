from tests.support.scenario import (
    EDIT_THEN_FINISH,
    FIXED,
    make_context,
    toggle_edits,
)
from veil.engine import Settings, resolve_settings, run

CHEAP = Settings().cheap_model
STRONG = Settings().strong_model


def test_a_failed_fix_gets_the_marker_label_of_the_settings_and_the_next_run_skips_it(
    tmp_path,
):
    settings = Settings(failed_fix_label="custom-failed")
    context, tracker, repos, _ = make_context(
        tmp_path, [], file="missing.py", settings=settings
    )

    first = run(context)
    second = run(context)

    assert first.outcomes == {"GR-100": "failed"}
    assert tracker.labels_on("GR-100") == ["custom-failed"]
    assert second.skipped == {"failed_fix": ["GR-100"]}
    assert repos.pull_requests == []


def test_the_review_status_of_the_settings_is_set_after_a_fix(tmp_path):
    settings = Settings(in_review_status="Code Review")
    context, tracker, repos, _ = make_context(
        tmp_path, EDIT_THEN_FINISH, settings=settings
    )

    run(context)

    assert tracker.status_of("GR-100") == "Code Review"
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED


def test_with_one_attempt_the_strong_model_never_runs(tmp_path):
    settings = Settings(step_cap=2, max_attempts=1)
    context, tracker, _, model = make_context(
        tmp_path, {CHEAP: toggle_edits(5)}, settings=settings
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "failed"}
    assert model.models_used == [CHEAP, CHEAP]
    assert tracker.labels_on("GR-100") == ["veil-failed-fix"]


def test_with_two_attempts_the_strong_model_gets_one_try(tmp_path):
    settings = Settings(step_cap=2, max_attempts=2)
    context, _, repos, model = make_context(
        tmp_path,
        {CHEAP: toggle_edits(5), STRONG: EDIT_THEN_FINISH},
        settings=settings,
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert STRONG in model.models_used
    assert len(repos.pull_requests) == 1


def test_a_tighter_repo_limit_reaches_the_run(tmp_path):
    settings = resolve_settings(org={"step_cap": 10}, repo={"step_cap": 2})
    context, _, _, _ = make_context(
        tmp_path, {CHEAP: toggle_edits(5), STRONG: toggle_edits(5)}, settings=settings
    )

    report = run(context)

    assert report.outcomes == {"GR-100": "failed"}
