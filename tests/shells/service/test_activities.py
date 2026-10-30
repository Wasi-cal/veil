import pytest
from temporalio.exceptions import ApplicationError

from tests.adapters.github.support import TOKEN, make_remote
from tests.shells.github_action.support import JIRA_TOKEN, OPENAI_KEY
from tests.shells.service.support import (
    FakeEngine,
    activity_env,
    make_deps,
    make_input,
    reports,
)
from veil.engine import RunReport
from veil.engine.errors.tracker_error import TrackerError
from veil.shells.service.activities import EngineActivities


def activities_for(tmp_path, stubs, engine, **changes):
    deps = make_deps(tmp_path, stubs, **changes)
    return EngineActivities(deps, run=engine), deps


def test_it_runs_the_engine_once_and_returns_the_run_report(tmp_path, stubs):
    engine = FakeEngine(reports(300, pull_requests=["https://example.invalid/pr/1"]))
    activities, _ = activities_for(tmp_path, stubs, engine)
    env, _ = activity_env()

    report = env.run(activities.run_engine, make_input())

    assert len(engine.contexts) == 1
    assert report.pull_requests == ["https://example.invalid/pr/1"]
    assert report.tokens_used == 300


def test_each_progress_report_becomes_a_heartbeat_with_the_tokens_used(tmp_path, stubs):
    def step(context):
        for used in (100, 250):
            context.report_progress(used)
        return RunReport(tokens_used=250)

    activities, _ = activities_for(tmp_path, stubs, FakeEngine(step))
    env, beats = activity_env()

    env.run(activities.run_engine, make_input())

    assert beats == [100, 250]


def test_a_retry_lowers_the_token_ceiling_by_the_tokens_of_the_last_heartbeat(
    tmp_path, stubs
):
    engine = FakeEngine(reports(300))
    activities, _ = activities_for(tmp_path, stubs, engine)
    env, beats = activity_env(prior_tokens=500)

    report = env.run(activities.run_engine, make_input(token_ceiling=2000))

    assert engine.contexts[0].settings.token_ceiling == 1500
    assert report.tokens_used == 800
    assert beats == [800]


def test_a_retry_with_a_used_up_budget_gives_the_engine_a_ceiling_of_zero(
    tmp_path, stubs
):
    engine = FakeEngine(reports(0))
    activities, _ = activities_for(tmp_path, stubs, engine)
    env, _ = activity_env(prior_tokens=5000)

    env.run(activities.run_engine, make_input(token_ceiling=2000))

    assert engine.contexts[0].settings.token_ceiling == 0


def test_the_settings_come_from_the_snapshot_in_the_input_and_not_from_the_database(
    tmp_path, stubs
):
    class Source:
        reads = 0

        def read_version(self):
            raise AssertionError("A retry must not read the settings again.")

        def read_snapshot(self, repos=()):
            Source.reads += 1
            raise AssertionError("A retry must not read the settings again.")

    engine = FakeEngine(reports())
    activities, _ = activities_for(tmp_path, stubs, engine, settings_source=Source())
    env, _ = activity_env()

    env.run(activities.run_engine, make_input(step_cap=7))

    assert engine.contexts[0].settings.step_cap == 7
    assert Source.reads == 0


def test_the_engine_gets_the_minted_token_and_the_other_credentials_and_nothing_else(
    tmp_path, stubs
):
    engine = FakeEngine(reports())
    activities, deps = activities_for(tmp_path, stubs, engine)
    env, _ = activity_env()

    env.run(activities.run_engine, make_input())

    assert set(engine.contexts[0].credential_values) == {TOKEN, JIRA_TOKEN, OPENAI_KEY}
    assert deps.token_source.minted == ["acme/app"]


def test_the_report_holds_no_credential(tmp_path, stubs):
    engine = FakeEngine(reports(5, outcomes={"SEC-1": "fixed"}))
    activities, _ = activities_for(tmp_path, stubs, engine)
    env, _ = activity_env()

    report = env.run(activities.run_engine, make_input())

    text = report.model_dump_json()
    assert all(value not in text for value in (TOKEN, JIRA_TOKEN, OPENAI_KEY))


@pytest.mark.parametrize("fails", [False, True])
def test_the_checkouts_are_deleted_after_the_run_even_when_it_fails(
    tmp_path, stubs, fails
):
    remote_root = tmp_path / "remote"
    remote_root.mkdir()
    make_remote(remote_root)
    seen = []

    def step(context):
        context.repo_provider.open_workspace("acme/app", "main")
        seen.extend((tmp_path / "checkouts").iterdir())
        if fails:
            raise TrackerError("down", status=503)
        return RunReport()

    deps = make_deps(tmp_path, stubs)
    deps = deps.model_copy(
        update={
            "urls": deps.urls.model_copy(
                update={"git_url": (remote_root / "remotes").as_uri()}
            )
        }
    )
    activities = EngineActivities(deps, run=FakeEngine(step))
    env, _ = activity_env()

    if fails:
        with pytest.raises(ApplicationError):
            env.run(activities.run_engine, make_input())
    else:
        env.run(activities.run_engine, make_input())

    assert seen
    assert list((tmp_path / "checkouts").iterdir()) == []


def test_an_engine_failure_becomes_a_temporal_error_with_a_redacted_message(
    tmp_path, stubs
):
    def step(context):
        raise TrackerError(f"Jira said no to {JIRA_TOKEN}", status=503)

    activities, _ = activities_for(tmp_path, stubs, FakeEngine(step))
    env, _ = activity_env()

    with pytest.raises(ApplicationError) as failure:
        env.run(activities.run_engine, make_input())

    assert failure.value.non_retryable is False
    assert JIRA_TOKEN not in str(failure.value)


def test_a_failed_fix_is_a_normal_result_and_not_an_error(tmp_path, stubs):
    engine = FakeEngine(reports(0, outcomes={"SEC-1": "failed"}))
    activities, _ = activities_for(tmp_path, stubs, engine)
    env, _ = activity_env()

    report = env.run(activities.run_engine, make_input())

    assert report.outcomes == {"SEC-1": "failed"}


def test_a_failed_mint_is_an_error_with_a_clear_message_and_the_engine_never_runs(
    tmp_path, stubs
):
    from tests.shells.service.support import FakeTokenSource
    from veil.engine.errors.repo_provider_error import RepoProviderError

    source = FakeTokenSource(
        error=RepoProviderError("The GitHub App is not installed.")
    )
    engine = FakeEngine(reports())
    activities, _ = activities_for(tmp_path, stubs, engine, token_source=source)
    env, _ = activity_env()

    with pytest.raises(ApplicationError, match="not installed") as failure:
        env.run(activities.run_engine, make_input())

    assert failure.value.type == "RepoProviderError"
    assert engine.contexts == []


def test_a_minted_token_that_looks_like_nothing_known_is_still_hidden_in_an_error(
    tmp_path, stubs
):
    from tests.shells.service.support import FakeTokenSource

    opaque = "opaque-installation-token-12345"

    def step(context):
        raise TrackerError(f"Failed with {opaque}.", status=503)

    activities, _ = activities_for(
        tmp_path, stubs, FakeEngine(step), token_source=FakeTokenSource(token=opaque)
    )
    env, _ = activity_env()

    with pytest.raises(ApplicationError) as failure:
        env.run(activities.run_engine, make_input())

    assert opaque not in str(failure.value)
