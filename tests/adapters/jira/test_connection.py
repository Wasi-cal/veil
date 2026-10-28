import base64

import pytest
from pydantic import SecretStr

from tests.adapters.jira.support import API_TOKEN, FIELDS, SEARCH, make_tracker
from tests.fakes.http_server import StubHttpServer
from tests.fakes.jira_fixtures import search_page
from veil.adapters.jira.gateway import resolve_api_base
from veil.adapters.jira.models.jira_credentials import JiraCredentials
from veil.adapters.jira.models.jira_settings import JiraSettings
from veil.adapters.jira.tracker import JiraTracker
from veil.engine.errors.tracker_error import TrackerError

EMAIL = "bot@example.invalid"


def authorization_of(server: StubHttpServer) -> str | None:
    return server.seen[0].authorization


def test_an_email_and_a_token_use_basic_authentication():
    with StubHttpServer() as server:
        server.routes[FIELDS] = (200, [])
        server.routes[SEARCH] = (200, search_page([]))

        make_tracker(server, email=EMAIL).open_tickets()

    expected = base64.b64encode(f"{EMAIL}:{API_TOKEN}".encode()).decode()
    assert authorization_of(server) == f"Basic {expected}"


def test_a_token_with_no_email_is_a_bearer_token():
    with StubHttpServer() as server:
        server.routes[FIELDS] = (200, [])
        server.routes[SEARCH] = (200, search_page([]))

        make_tracker(server, email=None).open_tickets()

    assert authorization_of(server) == f"Bearer {API_TOKEN}"


def test_an_error_names_the_status_and_never_holds_a_credential():
    basic = base64.b64encode(f"{EMAIL}:{API_TOKEN}".encode()).decode()
    with StubHttpServer() as server:
        server.routes[FIELDS] = (401, {"message": f"Bad {API_TOKEN} and {basic}"})

        with pytest.raises(TrackerError) as error:
            make_tracker(server).open_tickets()

    assert "401" in str(error.value)
    assert API_TOKEN not in str(error.value)
    assert basic not in str(error.value)


def test_a_reply_that_is_not_json_is_an_error():
    with StubHttpServer() as server:
        server.routes[FIELDS] = (200, [])
        server.routes[SEARCH] = (200, None)

        with pytest.raises(TrackerError):
            make_tracker(server).open_tickets()


def test_a_server_that_is_down_is_an_error_without_the_token():
    with StubHttpServer() as server:
        tracker = make_tracker(server)
    # The server has stopped. The port refuses the call.

    with pytest.raises(TrackerError) as error:
        tracker.open_tickets()

    assert API_TOKEN not in str(error.value)


def test_a_redirect_never_carries_the_credentials_to_another_host():
    with StubHttpServer() as elsewhere, StubHttpServer() as server:
        server.routes[FIELDS] = (
            302,
            {},
            {"Location": f"{elsewhere.url}/rest/api/3/field"},
        )

        with pytest.raises(TrackerError):
            make_tracker(server).open_tickets()

    assert elsewhere.seen == []


def test_the_credentials_do_not_show_in_repr_or_in_a_dump():
    credentials = JiraCredentials(email=EMAIL, api_token=SecretStr(API_TOKEN))

    assert API_TOKEN not in repr(credentials)
    assert API_TOKEN not in credentials.model_dump_json()


@pytest.mark.parametrize(
    "url",
    ["http://jira.example.invalid", "file:///etc/passwd", "ftp://x.invalid", "jira"],
)
def test_the_adapter_refuses_a_site_that_is_not_https(url):
    credentials = JiraCredentials(email=EMAIL, api_token=SecretStr(API_TOKEN))
    settings = JiraSettings(site_url=url, project_keys=("SEC",))

    with pytest.raises(TrackerError):
        JiraTracker(settings, credentials)
    with pytest.raises(TrackerError):
        resolve_api_base(url)


@pytest.mark.parametrize(
    "reply",
    [{}, {"issues": [{}]}, {"issues": [{"key": "SEC-1", "fields": None}]}, []],
    ids=["no issues", "issue with no key", "issue with no fields", "a list"],
)
def test_a_search_answer_in_an_unexpected_shape_is_a_tracker_error(reply):
    with StubHttpServer() as server:
        server.routes[FIELDS] = (200, [])
        server.routes[SEARCH] = (200, reply)

        with pytest.raises(TrackerError):
            make_tracker(server).open_tickets()


@pytest.mark.parametrize(
    "route_reply",
    [
        {"fields": None},
        {},
        {"fields": {"status": {}}},
    ],
)
def test_a_status_answer_in_an_unexpected_shape_is_a_tracker_error(route_reply):
    with StubHttpServer() as server:
        server.routes[("GET", "/rest/api/3/issue/SEC-7")] = (200, route_reply)

        with pytest.raises(TrackerError):
            make_tracker(server).set_status("SEC-7", "In Review")


def test_a_comment_page_in_an_unexpected_shape_is_a_tracker_error():
    with StubHttpServer() as server:
        server.routes[("GET", "/rest/api/3/issue/SEC-7/comment")] = (200, {"x": 1})

        with pytest.raises(TrackerError):
            make_tracker(server).add_comment("SEC-7", "Hello.")
