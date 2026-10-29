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
    metadata_cache=None,
    **settings,
) -> JiraTracker:
    return JiraTracker(
        settings=JiraSettings(
            site_url=server.url, project_keys=("SEC", "OPS"), **settings
        ),
        credentials=JiraCredentials(email=email, api_token=SecretStr(API_TOKEN)),
        api_base=server.url,
        metadata_cache=metadata_cache,
    )


# The id of the issue type of the ticket in the Jira stubs.
ISSUE_TYPE = "10001"
ISSUE = ("GET", "/rest/api/3/issue/SEC-7")
EDIT = ("PUT", "/rest/api/3/issue/SEC-7")
TRANSITIONS = ("GET", "/rest/api/3/issue/SEC-7/transitions")
DO_TRANSITION = ("POST", "/rest/api/3/issue/SEC-7/transitions")


def transition(identifier: str, target: str, category: str = "indeterminate") -> dict:
    return {
        "id": identifier,
        "name": f"Move to {target}",
        "to": {"name": target, "statusCategory": {"key": category}},
    }


def serve_status(
    server: StubHttpServer, current: str, transitions: list[dict] | None = None
) -> None:
    server.routes[ISSUE] = (
        200,
        {"fields": {"status": {"name": current}, "issuetype": {"id": ISSUE_TYPE}}},
    )
    server.routes[TRANSITIONS] = (200, {"transitions": transitions or []})
    server.routes[DO_TRANSITION] = (204, None)


def sent(server: StubHttpServer, route: tuple[str, str]):
    return [r for r in server.seen if (r.method, r.path) == route]


def reads(server: StubHttpServer, route: tuple[str, str]) -> int:
    return len([r for r in server.seen if (r.method, r.path) == route])
