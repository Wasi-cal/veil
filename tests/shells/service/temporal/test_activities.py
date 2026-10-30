import pytest
from temporalio.exceptions import ApplicationError

from tests.shells.github_action.support import JIRA_TOKEN
from tests.shells.service.support import FakeEngine, make_deps, reports
from tests.shells.service.temporal.support import activity_env, make_input
from veil.engine import RunReport
from veil.engine.errors.tracker_error import TrackerError
from veil.shells.service.temporal.activities import EngineActivities


def activities_for(tmp_path, stubs, engine, **changes):
    return EngineActivities(make_deps(tmp_path, stubs, **changes), run=engine)


def test_it_runs_the_engine_once_and_returns_the_run_report(tmp_path, stubs):
    engine = FakeEngine(reports(300, pull_requests=["https://example.invalid/pr/1"]))
    env, _ = activity_env()

    report = env.run(activities_for(tmp_path, stubs, engine).run_engine, make_input())

    assert len(engine.contexts) == 1
    assert report.pull_requests == ["https://example.invalid/pr/1"]
    assert report.tokens_used == 300


def test_each_progress_report_becomes_a_heartbeat_with_the_tokens_used(tmp_path, stubs):
    def step(context):
        for used in (100, 250):
            context.report_progress(used)
        return RunReport(tokens_used=250)

    env, beats = activity_env()

    env.run(activities_for(tmp_path, stubs, FakeEngine(step)).run_engine, make_input())

    assert beats == [100, 250]


def test_a_retry_lowers_the_token_ceiling_by_the_tokens_of_the_last_heartbeat(
    tmp_path, stubs
):
    engine = FakeEngine(reports(300))
    env, beats = activity_env(prior_tokens=500)

    report = env.run(
        activities_for(tmp_path, stubs, engine).run_engine,
        make_input(token_ceiling=2000),
    )

    assert engine.contexts[0].settings.token_ceiling == 1500
    assert report.tokens_used == 800
    assert beats == [800]


def test_an_attempt_with_no_earlier_heartbeat_uses_the_whole_ceiling(tmp_path, stubs):
    engine = FakeEngine(reports(0))
    env, _ = activity_env()

    env.run(
        activities_for(tmp_path, stubs, engine).run_engine,
        make_input(token_ceiling=2000),
    )

    assert engine.contexts[0].settings.token_ceiling == 2000


def test_an_infrastructure_failure_becomes_a_retryable_temporal_error_with_a_redacted_message(
    tmp_path, stubs
):
    def step(context):
        raise TrackerError(f"Jira said no to {JIRA_TOKEN}", status=503)

    env, _ = activity_env()

    with pytest.raises(ApplicationError) as failure:
        env.run(
            activities_for(tmp_path, stubs, FakeEngine(step)).run_engine, make_input()
        )

    assert failure.value.non_retryable is False
    assert failure.value.type == "TrackerError"
    assert JIRA_TOKEN not in str(failure.value)


def test_any_other_failure_becomes_a_non_retryable_temporal_error(tmp_path, stubs):
    def step(context):
        raise TrackerError("bad login", status=401)

    env, _ = activity_env()

    with pytest.raises(ApplicationError) as failure:
        env.run(
            activities_for(tmp_path, stubs, FakeEngine(step)).run_engine, make_input()
        )

    assert failure.value.non_retryable is True
