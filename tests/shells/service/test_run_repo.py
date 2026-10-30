import pytest

from tests.adapters.github.support import TOKEN, make_remote
from tests.shells.github_action.support import JIRA_TOKEN, OPENAI_KEY
from tests.shells.service.support import (
    FakeEngine,
    FakeTokenSource,
    make_deps,
    make_snapshot,
    reports,
)
from veil.engine import RunReport
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.errors.tracker_error import TrackerError
from veil.shells.service.errors.run_failed import RunFailed
from veil.shells.service.run_repo import run_repo


def run(
    tmp_path, stubs, engine, prior_tokens=0, progress=None, snapshot=None, **changes
):
    deps = make_deps(tmp_path, stubs, **changes)
    return run_repo(
        deps, "acme/app", snapshot or make_snapshot(), prior_tokens, progress, engine
    )


def test_it_runs_the_engine_once_and_returns_the_run_report(tmp_path, stubs):
    engine = FakeEngine(reports(300, pull_requests=["https://example.invalid/pr/1"]))

    report = run(tmp_path, stubs, engine)

    assert len(engine.contexts) == 1
    assert report.pull_requests == ["https://example.invalid/pr/1"]
    assert report.tokens_used == 300


def test_each_progress_report_goes_to_the_caller_with_the_tokens_used(tmp_path, stubs):
    def step(context):
        for used in (100, 250):
            context.report_progress(used)
        return RunReport(tokens_used=250)

    seen = []

    run(tmp_path, stubs, FakeEngine(step), progress=seen.append)

    assert seen == [100, 250]


def test_prior_tokens_lower_the_ceiling_and_count_in_the_report_and_the_progress(
    tmp_path, stubs
):
    engine = FakeEngine(reports(300))
    seen = []

    report = run(
        tmp_path,
        stubs,
        engine,
        prior_tokens=500,
        progress=seen.append,
        snapshot=make_snapshot(token_ceiling=2000),
    )

    assert engine.contexts[0].settings.token_ceiling == 1500
    assert report.tokens_used == 800
    assert seen == [800]


def test_used_up_prior_tokens_give_the_engine_a_ceiling_of_zero(tmp_path, stubs):
    engine = FakeEngine(reports(0))

    run(
        tmp_path,
        stubs,
        engine,
        prior_tokens=5000,
        snapshot=make_snapshot(token_ceiling=2000),
    )

    assert engine.contexts[0].settings.token_ceiling == 0


def test_the_settings_come_from_the_snapshot_and_not_from_the_database(tmp_path, stubs):
    class Source:
        def read_version(self):
            raise AssertionError("A run must not read the settings again.")

        def read_snapshot(self, repos=()):
            raise AssertionError("A run must not read the settings again.")

    engine = FakeEngine(reports())

    run(
        tmp_path,
        stubs,
        engine,
        snapshot=make_snapshot(step_cap=7),
        settings_source=Source(),
    )

    assert engine.contexts[0].settings.step_cap == 7


def test_the_engine_gets_the_minted_token_and_the_other_credentials_and_nothing_else(
    tmp_path, stubs
):
    engine = FakeEngine(reports())
    source = FakeTokenSource()

    run(tmp_path, stubs, engine, token_source=source)

    assert set(engine.contexts[0].credential_values) == {TOKEN, JIRA_TOKEN, OPENAI_KEY}
    assert source.minted == ["acme/app"]


def test_the_report_holds_no_credential(tmp_path, stubs):
    engine = FakeEngine(reports(5, outcomes={"SEC-1": "fixed"}))

    report = run(tmp_path, stubs, engine)

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

    if fails:
        with pytest.raises(RunFailed):
            run_repo(deps, "acme/app", make_snapshot(), run=FakeEngine(step))
    else:
        run_repo(deps, "acme/app", make_snapshot(), run=FakeEngine(step))

    assert seen
    assert list((tmp_path / "checkouts").iterdir()) == []


def test_an_engine_failure_is_a_run_failure_with_a_redacted_message(tmp_path, stubs):
    def step(context):
        raise TrackerError(f"Jira said no to {JIRA_TOKEN}", status=503)

    with pytest.raises(RunFailed) as failure:
        run(tmp_path, stubs, FakeEngine(step))

    assert failure.value.retryable is True
    assert JIRA_TOKEN not in str(failure.value)


def test_a_failed_fix_is_a_normal_result_and_not_an_error(tmp_path, stubs):
    engine = FakeEngine(reports(0, outcomes={"SEC-1": "failed"}))

    report = run(tmp_path, stubs, engine)

    assert report.outcomes == {"SEC-1": "failed"}


def test_a_failed_mint_is_a_run_failure_with_a_clear_message_and_the_engine_never_runs(
    tmp_path, stubs
):
    source = FakeTokenSource(
        error=RepoProviderError("The GitHub App is not installed.")
    )
    engine = FakeEngine(reports())

    with pytest.raises(RunFailed, match="not installed") as failure:
        run(tmp_path, stubs, engine, token_source=source)

    assert failure.value.error_type == "RepoProviderError"
    assert engine.contexts == []


def test_a_minted_token_that_looks_like_nothing_known_is_still_hidden_in_an_error(
    tmp_path, stubs
):
    opaque = "opaque-installation-token-12345"

    def step(context):
        raise TrackerError(f"Failed with {opaque}.", status=503)

    with pytest.raises(RunFailed) as failure:
        run(
            tmp_path,
            stubs,
            FakeEngine(step),
            token_source=FakeTokenSource(token=opaque),
        )

    assert opaque not in str(failure.value)
