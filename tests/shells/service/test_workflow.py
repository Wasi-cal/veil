import threading
from datetime import timedelta

import pytest
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ActivityError, ApplicationError

from tests.adapters.github.support import TOKEN
from tests.shells.github_action.support import JIRA_TOKEN, OPENAI_KEY, SITE
from tests.shells.service.support import FakeEngine, make_deps, reports
from tests.shells.service.temporal_support import (
    activity_scheduled,
    history_text,
    with_worker,
)
from veil.adapters.postgres.store import PostgresSettingsStore
from veil.engine import RunReport
from veil.engine.errors.tracker_error import TrackerError
from veil.shells.service.client import start_repo_run
from veil.shells.service.workflow_id import workflow_id


@pytest.fixture
def store(engine):
    store = PostgresSettingsStore(engine)
    store.set_org("jira_site_url", SITE, actor="test")
    store.set_org("jira_project_keys", ["SEC"], actor="test")
    return store


def deps_for(tmp_path, stubs, store):
    return make_deps(tmp_path, stubs, settings_source=store)


def run_one(host, deps, engine, repo="acme/app"):
    async def scenario(client, task_queue):
        handle = await start_repo_run(client, repo, task_queue)
        result = await handle.result()
        return handle, result, await handle.fetch_history()

    return with_worker(host, deps, engine, scenario)


def test_one_run_gives_the_report_of_the_engine(temporal_host, tmp_path, stubs, store):
    engine = FakeEngine(reports(40, pull_requests=["https://example.invalid/pr/7"]))

    handle, result, _ = run_one(
        temporal_host, deps_for(tmp_path, stubs, store), engine, "acme/one"
    )

    assert result.pull_requests == ["https://example.invalid/pr/7"]
    assert handle.id == workflow_id("acme/one")
    assert len(engine.contexts) == 1


def test_the_activity_limits_come_from_the_settings(
    temporal_host, tmp_path, stubs, store
):
    store.set_org("run_timeout_minutes", 5, actor="test")
    store.set_org("heartbeat_seconds", 30, actor="test")

    _, _, history = run_one(
        temporal_host,
        deps_for(tmp_path, stubs, store),
        FakeEngine(reports()),
        "acme/limits",
    )

    scheduled = activity_scheduled(history, "run_engine")
    assert scheduled.start_to_close_timeout.ToTimedelta() == timedelta(minutes=5)
    assert scheduled.heartbeat_timeout.ToTimedelta() == timedelta(seconds=30)
    assert scheduled.retry_policy.maximum_attempts == 2


def test_the_default_limits_are_one_hour_two_minutes_and_two_attempts(
    temporal_host, tmp_path, stubs, store
):
    _, _, history = run_one(
        temporal_host,
        deps_for(tmp_path, stubs, store),
        FakeEngine(reports()),
        "acme/defaults",
    )

    scheduled = activity_scheduled(history, "run_engine")
    assert scheduled.start_to_close_timeout.ToTimedelta() == timedelta(hours=1)
    assert scheduled.heartbeat_timeout.ToTimedelta() == timedelta(minutes=2)
    assert scheduled.retry_policy.maximum_attempts == 2


def test_no_credential_is_in_the_workflow_history(
    temporal_host, tmp_path, stubs, store
):
    def step(context):
        context.report_progress(10)
        return RunReport(tokens_used=10, outcomes={"SEC-1": "fixed"})

    _, _, history = run_one(
        temporal_host,
        deps_for(tmp_path, stubs, store),
        FakeEngine(step),
        "acme/secrets",
    )

    text = history_text(history)
    assert "SEC-1" in text
    for secret in (TOKEN, JIRA_TOKEN, OPENAI_KEY):
        assert secret not in text


def test_a_failure_message_in_the_history_never_holds_a_credential(
    temporal_host, tmp_path, stubs, store
):
    def step(context):
        raise TrackerError(
            f"bad login for {JIRA_TOKEN} and {TOKEN} and {OPENAI_KEY}", status=401
        )

    async def scenario(client, task_queue):
        handle = await start_repo_run(client, "acme/leak", task_queue)
        with pytest.raises(WorkflowFailureError):
            await handle.result()
        return await handle.fetch_history()

    history = with_worker(
        temporal_host, deps_for(tmp_path, stubs, store), FakeEngine(step), scenario
    )

    text = history_text(history)
    assert "bad login" in text
    assert JIRA_TOKEN not in text and TOKEN not in text and OPENAI_KEY not in text


def test_a_second_start_for_a_repo_joins_the_run_that_is_active(
    temporal_host, tmp_path, stubs, store
):
    release = threading.Event()

    def step(context):
        release.wait(20)
        return RunReport(tokens_used=1)

    engine = FakeEngine(step)

    async def scenario(client, task_queue):
        first = await start_repo_run(client, "acme/join", task_queue)
        second = await start_repo_run(client, "acme/join", task_queue)
        release.set()
        return first, second, await first.result(), await second.result()

    first, second, result_a, result_b = with_worker(
        temporal_host, deps_for(tmp_path, stubs, store), engine, scenario
    )

    assert first.id == second.id
    assert first.result_run_id == second.result_run_id
    assert result_a == result_b
    assert len(engine.contexts) == 1


def test_two_repos_run_in_two_workflows(temporal_host, tmp_path, stubs, store):
    engine = FakeEngine(reports())

    async def scenario(client, task_queue):
        a = await start_repo_run(client, "acme/a", task_queue)
        b = await start_repo_run(client, "acme/b", task_queue)
        await a.result()
        await b.result()
        return a, b

    a, b = with_worker(
        temporal_host, deps_for(tmp_path, stubs, store), engine, scenario
    )

    assert a.id != b.id
    assert len(engine.contexts) == 2
    assert {c.tracker.__class__.__name__ for c in engine.contexts} == {
        "RepoScopedTracker"
    }


def test_a_failed_fix_is_a_normal_result_and_never_causes_a_retry(
    temporal_host, tmp_path, stubs, store
):
    engine = FakeEngine(reports(5, outcomes={"SEC-1": "failed"}))

    _, result, _ = run_one(
        temporal_host, deps_for(tmp_path, stubs, store), engine, "acme/ff"
    )

    assert result.outcomes == {"SEC-1": "failed"}
    assert len(engine.contexts) == 1


def test_an_infrastructure_failure_is_tried_again_and_the_second_attempt_keeps_the_budget_and_the_settings(
    temporal_host, tmp_path, stubs, store
):
    def first(context):
        context.report_progress(500)
        store.set_org("step_cap", 3, actor="test")
        raise TrackerError("Jira is down.", status=503)

    def second(context):
        context.report_progress(100)
        return RunReport(tokens_used=100)

    engine = FakeEngine(first, second)

    _, result, _ = run_one(
        temporal_host, deps_for(tmp_path, stubs, store), engine, "acme/retry"
    )

    assert len(engine.contexts) == 2
    before, after = (c.settings for c in engine.contexts)
    assert before.step_cap == after.step_cap == 25
    assert after.token_ceiling == before.token_ceiling - 500
    assert result.tokens_used == 600


def test_the_retry_is_bounded_to_two_attempts(temporal_host, tmp_path, stubs, store):
    def step(context):
        raise TrackerError("Jira is down.", status=503)

    engine = FakeEngine(step)

    async def scenario(client, task_queue):
        handle = await start_repo_run(client, "acme/bound", task_queue)
        with pytest.raises(WorkflowFailureError) as failure:
            await handle.result()
        return failure.value

    failure = with_worker(
        temporal_host, deps_for(tmp_path, stubs, store), engine, scenario
    )

    assert len(engine.contexts) == 2
    assert isinstance(failure.cause, ActivityError)
    assert isinstance(failure.cause.cause, ApplicationError)


def test_a_failure_that_cannot_work_later_is_not_retried(
    temporal_host, tmp_path, stubs, store
):
    def step(context):
        raise TrackerError("Bad login.", status=401)

    engine = FakeEngine(step)

    async def scenario(client, task_queue):
        handle = await start_repo_run(client, "acme/noretry", task_queue)
        with pytest.raises(WorkflowFailureError):
            await handle.result()

    with_worker(temporal_host, deps_for(tmp_path, stubs, store), engine, scenario)

    assert len(engine.contexts) == 1
