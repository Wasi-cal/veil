import io
from pathlib import Path

import yaml

from tests.adapters.github.support import TOKEN
from tests.adapters.jira.support import API_TOKEN as JIRA_TOKEN
from tests.fakes.http_server import StubHttpServer
from tests.support.secret_samples import KEY_LIKE
from veil.engine import Context, RunReport
from veil.shells.shared.models.service_urls import ServiceUrls

OPENAI_KEY = KEY_LIKE["sk-key"]
JIRA_EMAIL = "bot@example.invalid"
SITE = "https://acme.example.invalid"
SEARCH = ("POST", "/rest/api/3/search/jql")
FIELDS = ("GET", "/rest/api/3/field")


class SpyRun:
    """Stands in for the Engine. It keeps the context and what the Action had printed at that time."""

    def __init__(self, out: io.StringIO, report: RunReport | None = None, error=None):
        self.out = out
        self.report = report or RunReport()
        self.error = error
        self.contexts: list[Context] = []
        self.printed_before: list[str] = []

    def __call__(self, context: Context) -> RunReport:
        self.contexts.append(context)
        self.printed_before.append(self.out.getvalue())
        if self.error:
            raise self.error
        return self.report


class World:
    def __init__(self, tmp_path: Path, jira: StubHttpServer, github: StubHttpServer):
        self.tmp_path = tmp_path
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir()
        self.summary = tmp_path / "summary.md"
        self.jira = jira
        self.github = github
        self.out = io.StringIO()
        self.environ = {
            "GITHUB_REPOSITORY": "acme/app",
            "GITHUB_WORKSPACE": str(self.workspace),
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "JIRA_EMAIL": JIRA_EMAIL,
            "JIRA_API_TOKEN": JIRA_TOKEN,
            "OPENAI_API_KEY": OPENAI_KEY,
            "GITHUB_TOKEN": TOKEN,
        }
        self.write_settings({"jira_site_url": SITE, "jira_project_keys": ["SEC"]})
        jira.routes[FIELDS] = (200, [])
        jira.routes[SEARCH] = (200, {"issues": [], "isLast": True})

    def write_settings(self, settings: dict) -> None:
        folder = self.workspace / ".gozu"
        folder.mkdir(exist_ok=True)
        (folder / "jira-to-pr.yml").write_text(yaml.safe_dump(settings))

    @property
    def urls(self) -> ServiceUrls:
        return ServiceUrls(
            github_api_url=self.github.url,
            jira_api_base=self.jira.url,
            openai_api_url=self.github.url,
        )

    def run_action(self, run=None, **changes):
        from veil.shells.github_action.run_action import run_action

        self.environ.update(changes)
        spy = run if run is not None else SpyRun(self.out)
        code = run_action(self.environ, urls=self.urls, run=spy, out=self.out)
        return code, spy
