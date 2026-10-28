from pydantic import SecretStr

from tests.fakes.http_server import StubHttpServer
from veil.adapters.jira.models.jira_credentials import JiraCredentials
from veil.adapters.jira.models.jira_settings import JiraSettings
from veil.adapters.jira.tracker import JiraTracker

API_TOKEN = "".join(["ATATT3", "xFfGF0aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0"])  # noqa: FLY002
SEARCH = ("POST", "/rest/api/3/search/jql")
FIELDS = ("GET", "/rest/api/3/field")


def make_tracker(
    server: StubHttpServer,
    email: str | None = "bot@example.invalid",
    **settings,
) -> JiraTracker:
    return JiraTracker(
        settings=JiraSettings(
            site_url=server.url, project_keys=("SEC", "OPS"), **settings
        ),
        credentials=JiraCredentials(email=email, api_token=SecretStr(API_TOKEN)),
        api_base=server.url,
    )
