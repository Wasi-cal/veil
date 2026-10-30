from pydantic import SecretStr

from tests.shells.github_action.support import (
    JIRA_EMAIL,
    JIRA_TOKEN,
    OPENAI_KEY,
    SITE,
    FakeTokenSource,
)
from veil.adapters.postgres.models.settings_snapshot import SettingsSnapshot
from veil.engine import Context, RunReport
from veil.shells.service.models.service_dependencies import ServiceDependencies
from veil.shells.shared.models.run_credentials import RunCredentials
from veil.shells.shared.models.service_urls import ServiceUrls

__all__ = [
    "FakeEngine",
    "FakeTokenSource",
    "make_deps",
    "make_snapshot",
    "reports",
]


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


def make_snapshot(repo: str = "acme/app", **org) -> SettingsSnapshot:
    return SettingsSnapshot(
        version=1,
        org={"jira_site_url": SITE, "jira_project_keys": ["SEC"], **org},
        repos={repo: {}},
    )
