from tests.adapters.jira.support import FIELDS, SEARCH, make_tracker
from tests.fakes.http_server import StubHttpServer
from tests.fakes.jira_fixtures import gozurion_details, issue_json, search_page

EXPECTED_JQL = (
    'project in ("SEC", "OPS") AND labels = "veil-eligible" '
    "AND statusCategory != Done AND assignee is EMPTY ORDER BY key ASC"
)


def serve(server: StubHttpServer, *pages: dict) -> None:
    server.routes[FIELDS] = (200, [])
    server.routes[SEARCH] = [(200, page) for page in pages]


def test_a_gozurion_ticket_becomes_a_ticket_with_the_exact_branch():
    with StubHttpServer() as server:
        serve(server, search_page([issue_json()]))

        [ticket] = make_tracker(server).open_tickets()

    assert ticket.key == "SEC-7"
    assert ticket.repo == "acme/app"
    assert ticket.file == "src/app.py"
    assert ticket.line == 3
    assert ticket.severity == "HIGH"
    assert ticket.branch == "feature/login"
    assert ticket.finding == (
        "Avoid eval on user input. It runs code that comes from a user."
    )
    assert ticket.issue_label == "issue-3f9a"


def test_the_ticket_carries_every_label_so_the_failed_fix_marker_shows():
    labels = ("issue-3f9a", "veil-eligible", "veil-failed-fix")
    with StubHttpServer() as server:
        serve(server, search_page([issue_json(labels=labels)]))

        [ticket] = make_tracker(server).open_tickets()

    assert ticket.labels == labels


def test_the_search_asks_for_open_unassigned_tickets_with_the_eligible_label():
    with StubHttpServer() as server:
        serve(server, search_page([]))

        make_tracker(server).open_tickets()

    [search] = [r for r in server.seen if (r.method, r.path) == SEARCH]
    assert search.body["jql"] == EXPECTED_JQL


def test_the_eligible_label_comes_from_the_settings():
    with StubHttpServer() as server:
        serve(server, search_page([]))

        make_tracker(server, eligible_label="fix-me").open_tickets()

    [search] = [r for r in server.seen if (r.method, r.path) == SEARCH]
    assert 'labels = "fix-me"' in search.body["jql"]


def test_an_empty_eligible_label_asks_for_every_open_ticket_without_an_assignee():
    with StubHttpServer() as server:
        serve(server, search_page([]))

        make_tracker(server, eligible_label="").open_tickets()

    [search] = [r for r in server.seen if (r.method, r.path) == SEARCH]
    assert search.body["jql"] == (
        'project in ("SEC", "OPS") '
        "AND statusCategory != Done AND assignee is EMPTY ORDER BY key ASC"
    )


def test_every_page_of_the_search_is_read():
    with StubHttpServer() as server:
        serve(
            server,
            search_page([issue_json("SEC-1")], next_page_token="page-2"),
            search_page([issue_json("SEC-2")]),
        )

        tickets = make_tracker(server).open_tickets()

    assert [t.key for t in tickets] == ["SEC-1", "SEC-2"]
    searches = [r for r in server.seen if (r.method, r.path) == SEARCH]
    assert searches[1].body["nextPageToken"] == "page-2"


def test_a_ticket_that_is_not_a_finding_of_one_line_or_has_no_branch_is_skipped():
    rollup = issue_json("SEC-8", details=["Repository: acme/app", "Source: sonarqube"])
    no_line = issue_json("SEC-9", details=gozurion_details(line=None))
    no_branch = issue_json(
        "SEC-10",
        details=[d for d in gozurion_details() if not d.startswith("Branch:")],
    )
    with StubHttpServer() as server:
        serve(server, search_page([rollup, no_line, no_branch, issue_json()]))

        tickets = make_tracker(server).open_tickets()

    assert [t.key for t in tickets] == ["SEC-7"]


def test_a_scanner_that_gives_a_plain_path_works_too():
    details = gozurion_details(component="src/app.py")
    with StubHttpServer() as server:
        serve(server, search_page([issue_json(details=details)]))

        [ticket] = make_tracker(server).open_tickets()

    assert ticket.file == "src/app.py"


def test_a_bullet_in_the_finding_text_never_beats_the_details_list():
    full = "Avoid eval."
    issue = issue_json(summary="Careful.", full=full)
    first = issue["fields"]["description"]["content"][0]
    first["content"][0]["text"] = "Careful."
    issue["fields"]["description"]["content"].insert(
        0,
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Line: 99"}],
                        }
                    ],
                }
            ],
        },
    )
    with StubHttpServer() as server:
        serve(server, search_page([issue]))

        [ticket] = make_tracker(server).open_tickets()

    assert ticket.line == 3


def test_a_path_with_a_colon_keeps_its_folders():
    details = gozurion_details(component="src/a:b.py")
    with StubHttpServer() as server:
        serve(server, search_page([issue_json(details=details)]))

        [ticket] = make_tracker(server).open_tickets()

    assert ticket.file == "src/a:b.py"


def test_a_line_that_a_number_field_gives_as_a_float_works():
    details = ["Repository: acme/app", "Branch: feature/login"]
    issue = issue_json(
        details=details,
        extra_fields={
            "customfield_10100": "acme_app:src/app.py",
            "customfield_10101": 12.0,
            "customfield_10102": {"value": "HIGH"},
        },
    )
    with StubHttpServer() as server:
        server.routes[FIELDS] = (
            200,
            [
                {"id": "customfield_10100", "name": "SonarQube Component"},
                {"id": "customfield_10101", "name": "SonarQube Line"},
                {"id": "customfield_10102", "name": "SonarQube Severity"},
            ],
        )
        server.routes[SEARCH] = (200, search_page([issue]))

        [ticket] = make_tracker(server).open_tickets()

    assert (ticket.line, ticket.severity) == (12, "HIGH")


def test_the_custom_fields_of_gozurion_fill_the_ticket_when_the_details_lack_them():
    details = ["Repository: acme/app", "Type: vulnerability", "Branch: feature/login"]
    issue = issue_json(
        details=details,
        extra_fields={
            "customfield_10100": "acme_app:src/app.py",
            "customfield_10101": 3,
            "customfield_10102": "HIGH",
        },
    )
    with StubHttpServer() as server:
        server.routes[FIELDS] = (
            200,
            [
                {"id": "customfield_10100", "name": "SonarQube Component"},
                {"id": "customfield_10101", "name": "SonarQube Line"},
                {"id": "customfield_10102", "name": "SonarQube Severity"},
                {"id": "customfield_10999", "name": "Another field"},
            ],
        )
        server.routes[SEARCH] = (200, search_page([issue]))

        [ticket] = make_tracker(server).open_tickets()

    assert (ticket.file, ticket.line, ticket.severity) == ("src/app.py", 3, "HIGH")
    [search] = [r for r in server.seen if (r.method, r.path) == SEARCH]
    assert set(search.body["fields"]) == {
        "labels",
        "description",
        "customfield_10100",
        "customfield_10101",
        "customfield_10102",
    }
