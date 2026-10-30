import dataclasses

from pydantic import SecretStr
from temporalio.testing import ActivityEnvironment

from tests.shells.github_action.support import (
    JIRA_EMAIL,
    JIRA_TOKEN,
    OPENAI_KEY,
    SITE,
    FakeTokenSource,
)
from veil.adapters.postgres.models.settings_snapshot import SettingsSnapshot
from veil.engine import Context, RunReport
from veil.shells.service.models.run_engine_input import RunEngineInput
from veil.shells.service.models.service_dependencies import ServiceDependencies
from veil.shells.shared.models.run_credentials import RunCredentials
from veil.shells.shared.models.service_urls import ServiceUrls

__all__ = ["FakeEngine", "FakeTokenSource", "activity_env", "make_deps", "make_input"]


class FakeEngine:
    """Stands in for `run`. It keeps each context. A script says what each call does."""

    def __init__(self, *steps):
        self.steps = list(steps)
        self.contexts: list[Context] = []

    def __call__(self, context: Context) -> RunReport:
        self.contexts.append(context)
        step = self.steps.pop(0) if len(self.steps) > 1 else self.steps[0]
        return step(context)


def reports(tokens: int = 0, **fields):
    """A step that reports its progress and returns a report."""

    def step(context: Context) -> RunReport:
        context.report_progress(tokens)
        return RunReport(tokens_used=tokens, **fields)

    return step


class UnusedSource:
    """A settings source for a test that must not read settings."""

    def read_version(self) -> int:
        raise AssertionError("This test must not read the settings.")

    def read_snapshot(self, repos=()):
        raise AssertionError("This test must not read the settings.")


def make_deps(tmp_path, stubs, token_source=None, settings_source=None, **changes):
    jira, github = stubs
    return ServiceDependencies(
        token_source=token_source or FakeTokenSource(),
        settings_source=settings_source or UnusedSource(),
        credentials=RunCredentials(
            jira_email=JIRA_EMAIL,
            jira_token=SecretStr(JIRA_TOKEN),
            openai_key=SecretStr(OPENAI_KEY),
        ),
        checkout_root=tmp_path / "checkouts",
        urls=ServiceUrls(
            github_api_url=github.url,
            jira_api_base=jira.url,
            openai_api_url=github.url,
        ),
        **changes,
    )


def make_input(repo: str = "acme/app", **org) -> RunEngineInput:
    return RunEngineInput(
        repo=repo,
        snapshot=SettingsSnapshot(
            version=1,
            org={"jira_site_url": SITE, "jira_project_keys": ["SEC"], **org},
            repos={repo: {}},
        ),
    )


def activity_env(prior_tokens: int | None = None):
    """An activity environment and the list of heartbeats. A prior heartbeat is what an earlier attempt sent."""
    env = ActivityEnvironment()
    beats: list[int] = []
    env.on_heartbeat = lambda *details: beats.append(details[0])
    if prior_tokens is not None:
        env.info = dataclasses.replace(env.info, heartbeat_details=[prior_tokens])
    return env, beats
