import logging
import tempfile

import pytest

from tests.adapters.github.support import make_remote
from tests.shells.github_action.support import JIRA_TOKEN, SpyRun
from veil.engine import RunReport
from veil.engine.errors.model_client_error import ModelClientError
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.errors.tracker_error import TrackerError
from veil.engine.models.report.ticket_usage import ModelTokens, TicketUsage
from veil.shells.github_action.run_action import run_action


@pytest.mark.parametrize(
    "error",
    [
        RepoProviderError("The repo failed."),
        TrackerError("The tracker failed."),
        ModelClientError("The model failed."),
    ],
)
def test_an_engine_error_fails_the_run_with_the_message(world, error):
    code, _ = world.run_action(run=SpyRun(world.out, error=error))

    assert code == 1
    assert f"::error::{error}" in world.out.getvalue()


def test_the_failure_text_hides_the_credentials_of_the_run(world):
    error = TrackerError(f"Jira said no to {JIRA_TOKEN}.")

    world.run_action(run=SpyRun(world.out, error=error))

    assert JIRA_TOKEN not in world.out.getvalue().replace(
        f"::add-mask::{JIRA_TOKEN}", ""
    )
    assert "::error::" in world.out.getvalue()


def test_a_settings_error_fails_the_run_before_the_run_starts(world):
    world.write_settings({"step_capp": 5})

    code, spy = world.run_action()

    assert code == 1
    assert "step_capp" in world.out.getvalue()
    assert spy.contexts == []


def test_a_bad_repository_name_fails_the_run(world):
    code, spy = world.run_action(GITHUB_REPOSITORY="acme/app/../other")

    assert code == 1
    assert spy.contexts == []


def test_the_checkouts_are_deleted_even_when_the_engine_fails(world, monkeypatch):
    scratch = world.tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    remote_root = world.tmp_path / "remote"
    remote_root.mkdir()
    make_remote(remote_root)
    checked_out = []

    class Checkout(SpyRun):
        def __call__(self, context):
            context.repo_provider.open_workspace("acme/app", "main")
            checked_out.extend(scratch.iterdir())
            return super().__call__(context)

    urls = world.urls.model_copy(update={"git_url": (remote_root / "remotes").as_uri()})
    code = run_action(
        world.environ,
        urls=urls,
        run=Checkout(world.out, error=TrackerError("boom")),
        out=world.out,
    )

    assert code == 1
    assert checked_out
    assert list(scratch.iterdir()) == []


def test_the_report_goes_to_the_step_summary_and_a_failed_fix_is_not_a_failure(world):
    report = RunReport(
        pull_requests=["https://github.example.invalid/acme/app/pull/9"],
        outcomes={"SEC-1": "fixed", "SEC-2": "failed"},
        reasons={"SEC-2": "The file a|b.js is not a text file.\nSecond line."},
        usage={
            "SEC-1": TicketUsage(
                by_model={"small": ModelTokens(input=700, output=100, total=800)}
            ),
            "SEC-2": TicketUsage(
                by_model={
                    "small": ModelTokens(input=300, output=100, total=400),
                    "big": ModelTokens(input=20, output=14, total=34),
                },
                escalated=True,
            ),
        },
        tokens_used=1234,
    )

    code, _ = world.run_action(run=SpyRun(world.out, report=report))

    assert code == 0
    text = world.summary.read_text()
    assert "https://github.example.invalid/acme/app/pull/9" in text
    assert "SEC-2" in text
    assert "1234" in text
    assert "Tokens used: 1234 (input 1020, output 214)" in text
    assert (
        "| SEC-2 | failed | 320 | 114 | 434 | yes |"
        " The file a\\|b.js is not a text file. Second line. |"
    ) in text
    assert "| SEC-1 | fixed | 700 | 100 | 800 | no |  |" in text
    escalated = text.split("### Escalated tickets")[1]
    assert "| SEC-2 | small | 300 | 100 | 400 |" in escalated
    assert "| SEC-2 | big | 20 | 14 | 34 |" in escalated
    assert "SEC-1" not in escalated


def test_a_run_without_escalation_has_no_escalated_table(world):
    report = RunReport(outcomes={"SEC-1": "skipped"}, tokens_used=0)

    world.run_action(run=SpyRun(world.out, report=report))

    text = world.summary.read_text()
    assert "Escalated tickets" not in text
    assert "| SEC-1 | skipped |  |  |  |  |  |" in text


def test_the_log_of_the_engine_goes_to_the_output_during_the_run_only(world):
    class Chatty(SpyRun):
        def __call__(self, context):
            logging.getLogger("veil.engine.run").info("SEC-1: start.")
            return super().__call__(context)

    world.run_action(run=Chatty(world.out))

    assert "SEC-1: start." in world.out.getvalue()
    assert logging.getLogger("veil").handlers == []


def test_no_summary_file_is_needed(world):
    del world.environ["GITHUB_STEP_SUMMARY"]

    code, _ = world.run_action()

    assert code == 0
