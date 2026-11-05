from tests.adapters.jira.support import FIELDS, SEARCH, make_tracker
from tests.fakes.http_server import StubHttpServer
from tests.fakes.jira_fixtures import issue_json, search_page

OPEN = {
    "status": {"statusCategory": {"key": "new"}},
    "assignee": None,
}


def route(key: str) -> tuple[str, str]:
    return ("GET", f"/rest/api/3/issue/{key}")


def serve(server: StubHttpServer, found=(), **issues: dict) -> None:
    server.routes[FIELDS] = (200, [])
    server.routes[SEARCH] = (200, search_page(list(found)))
    for key, issue in issues.items():
        server.routes[route(key.replace("_", "-"))] = (200, issue)


def issue(key: str, **fields) -> dict:
    return issue_json(key=key, extra_fields={**OPEN, **fields})


def keys_of(server, *extra) -> list[str]:
    return [t.key for t in make_tracker(server, extra_keys=extra).open_tickets()]


def test_a_new_ticket_that_search_does_not_show_yet_is_read_by_its_key():
    with StubHttpServer() as server:
        serve(server, SEC_9=issue("SEC-9"))

        assert keys_of(server, "SEC-9") == ["SEC-9"]


def test_a_ticket_that_search_shows_is_not_read_again_or_listed_twice():
    with StubHttpServer() as server:
        serve(server, found=[issue_json(key="SEC-9")])

        assert keys_of(server, "SEC-9") == ["SEC-9"]

    assert route("SEC-9") not in [(r.method, r.path) for r in server.seen]


def test_a_ticket_that_the_search_would_leave_out_is_left_out_by_key_too():
    cases = {
        "SEC_1": issue("SEC-1", status={"statusCategory": {"key": "done"}}),
        "SEC_2": issue("SEC-2", assignee={"accountId": "abc"}),
        "SEC_3": issue("SEC-3", labels=["issue-3f9a"]),
    }
    with StubHttpServer() as server:
        serve(server, **cases)

        assert keys_of(server, "SEC-1", "SEC-2", "SEC-3") == []


def test_a_key_that_is_not_a_jira_key_of_the_projects_is_never_requested():
    with StubHttpServer() as server:
        serve(server)

        assert keys_of(server, "../../x", "OTHER-1", "sec-1", "SEC-1; DROP") == []

    paths = [r.path for r in server.seen if r.method == "GET"]
    assert paths == [FIELDS[1]]


def test_a_key_that_jira_does_not_know_is_skipped_and_the_rest_still_work():
    with StubHttpServer() as server:
        serve(server, SEC_9=issue("SEC-9"))
        server.routes[route("SEC-8")] = (
            404,
            {"errorMessages": ["Issue does not exist"]},
        )

        assert keys_of(server, "SEC-8", "SEC-9") == ["SEC-9"]
