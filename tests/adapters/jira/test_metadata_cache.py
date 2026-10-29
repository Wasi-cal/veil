import pytest

from tests.adapters.jira.support import (
    DO_TRANSITION,
    FIELDS,
    ISSUE_TYPE,
    SEARCH,
    TRANSITIONS,
    make_tracker,
    reads,
    sent,
    serve_status,
    transition,
)
from tests.fakes.http_server import StubHttpServer
from tests.fakes.jira_fixtures import search_page
from veil.engine.errors.tracker_error import TrackerError


class DictMetadataCache:
    """A cache in memory. It keeps what the tracker gives it."""

    def __init__(self):
        self.fields = None
        self.moves = {}

    def field_ids(self):
        return self.fields

    def store_field_ids(self, ids):
        self.fields = ids

    def transitions(self, project, issue_type, status):
        return self.moves.get((project, issue_type, status))

    def store_transitions(self, project, issue_type, status, transitions):
        self.moves[(project, issue_type, status)] = transitions

    def forget_transitions(self, project, issue_type, status):
        self.moves.pop((project, issue_type, status), None)


def serve_search(server):
    server.routes[FIELDS] = (
        200,
        [{"id": "customfield_10100", "name": "SonarQube Component"}],
    )
    server.routes[SEARCH] = (200, search_page([]))


def test_the_custom_field_ids_are_read_once_and_then_come_from_the_cache():
    cache = DictMetadataCache()
    with StubHttpServer() as server:
        serve_search(server)

        make_tracker(server, metadata_cache=cache).open_tickets()
        make_tracker(server, metadata_cache=cache).open_tickets()

    assert reads(server, FIELDS) == 1
    assert reads(server, SEARCH) == 2
    assert cache.fields == {"SonarQube Component": "customfield_10100"}


def test_a_site_with_no_custom_fields_is_cached_as_such_and_not_asked_again():
    cache = DictMetadataCache()
    with StubHttpServer() as server:
        server.routes[FIELDS] = (200, [])
        server.routes[SEARCH] = (200, search_page([]))

        make_tracker(server, metadata_cache=cache).open_tickets()
        make_tracker(server, metadata_cache=cache).open_tickets()

    assert reads(server, FIELDS) == 1
    assert cache.fields == {}


def test_the_transitions_of_a_project_and_a_status_are_read_once():
    cache = DictMetadataCache()
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("31", "In Review")])
        server.routes[("GET", "/rest/api/3/issue/SEC-8")] = (
            200,
            {"fields": {"status": {"name": "To Do"}, "issuetype": {"id": ISSUE_TYPE}}},
        )
        server.routes[("POST", "/rest/api/3/issue/SEC-8/transitions")] = (204, None)
        tracker = make_tracker(server, metadata_cache=cache)

        tracker.set_status("SEC-7", "In Review")
        tracker.set_status("SEC-8", "In Review")

    assert reads(server, TRANSITIONS) == 1
    assert len(sent(server, DO_TRANSITION)) == 1
    second_post = next(
        r
        for r in server.seen
        if r.method == "POST" and r.path.endswith("SEC-8/transitions")
    )
    assert second_post.body == {"transition": {"id": "31"}}


def test_the_status_of_each_ticket_is_always_read_live_and_a_ticket_in_place_is_not_moved():
    cache = DictMetadataCache()
    cache.store_transitions("SEC", ISSUE_TYPE, "To Do", [transition("31", "In Review")])
    with StubHttpServer() as server:
        serve_status(server, "In Review")

        make_tracker(server, metadata_cache=cache).set_status("SEC-7", "In Review")

    assert reads(server, ("GET", "/rest/api/3/issue/SEC-7")) == 1
    assert sent(server, DO_TRANSITION) == []


def test_another_status_has_its_own_entry():
    cache = DictMetadataCache()
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("31", "In Review")])
        make_tracker(server, metadata_cache=cache).set_status("SEC-7", "In Review")
        serve_status(server, "In Progress", [transition("32", "In Review")])

        make_tracker(server, metadata_cache=cache).set_status("SEC-7", "In Review")

    assert set(cache.moves) == {
        ("SEC", ISSUE_TYPE, "To Do"),
        ("SEC", ISSUE_TYPE, "In Progress"),
    }


@pytest.mark.parametrize("status", [400, 404, 409])
def test_a_cached_transition_that_the_workflow_no_longer_accepts_is_read_live_once_and_retried(
    status,
):
    cache = DictMetadataCache()
    cache.store_transitions("SEC", ISSUE_TYPE, "To Do", [transition("99", "In Review")])
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("31", "In Review")])
        server.routes[DO_TRANSITION] = [
            (status, {"errorMessages": ["The transition is not valid."]}),
            (204, None),
        ]

        make_tracker(server, metadata_cache=cache).set_status("SEC-7", "In Review")

    posts = sent(server, DO_TRANSITION)
    assert [p.body for p in posts] == [
        {"transition": {"id": "99"}},
        {"transition": {"id": "31"}},
    ]
    assert reads(server, TRANSITIONS) == 1
    assert cache.moves[("SEC", ISSUE_TYPE, "To Do")][0]["id"] == "31"


@pytest.mark.parametrize("status", [401, 403, 500, 502])
def test_a_failure_that_is_not_about_the_workflow_is_never_retried_and_keeps_the_entry(
    status,
):
    cache = DictMetadataCache()
    cache.store_transitions("SEC", ISSUE_TYPE, "To Do", [transition("31", "In Review")])
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("31", "In Review")])
        server.routes[DO_TRANSITION] = (status, {"message": "failed"})

        with pytest.raises(TrackerError):
            make_tracker(server, metadata_cache=cache).set_status("SEC-7", "In Review")

    assert len(sent(server, DO_TRANSITION)) == 1
    assert reads(server, TRANSITIONS) == 0
    assert ("SEC", ISSUE_TYPE, "To Do") in cache.moves


def test_the_transitions_are_stored_only_after_a_move_that_worked():
    cache = DictMetadataCache()
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("31", "In Review")])
        server.routes[DO_TRANSITION] = (500, {"message": "failed"})

        with pytest.raises(TrackerError):
            make_tracker(server, metadata_cache=cache).set_status("SEC-7", "In Review")

    assert cache.moves == {}


def test_each_issue_type_has_its_own_transitions_because_each_can_have_its_own_workflow():
    cache = DictMetadataCache()
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("31", "In Review")])
        server.routes[("GET", "/rest/api/3/issue/SEC-8")] = (
            200,
            {"fields": {"status": {"name": "To Do"}, "issuetype": {"id": "10002"}}},
        )
        server.routes[("GET", "/rest/api/3/issue/SEC-8/transitions")] = (
            200,
            {"transitions": [transition("77", "In Review")]},
        )
        server.routes[("POST", "/rest/api/3/issue/SEC-8/transitions")] = (204, None)
        tracker = make_tracker(server, metadata_cache=cache)

        tracker.set_status("SEC-7", "In Review")
        tracker.set_status("SEC-8", "In Review")

    assert set(cache.moves) == {("SEC", ISSUE_TYPE, "To Do"), ("SEC", "10002", "To Do")}
    second = next(
        r
        for r in server.seen
        if r.method == "POST" and r.path.endswith("SEC-8/transitions")
    )
    assert second.body == {"transition": {"id": "77"}}


def test_a_ticket_with_no_issue_type_in_the_answer_never_uses_the_cache():
    cache = DictMetadataCache()
    cache.store_transitions("SEC", ISSUE_TYPE, "To Do", [transition("99", "In Review")])
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("31", "In Review")])
        server.routes[("GET", "/rest/api/3/issue/SEC-7")] = (
            200,
            {"fields": {"status": {"name": "To Do"}}},
        )

        make_tracker(server, metadata_cache=cache).set_status("SEC-7", "In Review")

    assert [p.body for p in sent(server, DO_TRANSITION)] == [
        {"transition": {"id": "31"}}
    ]
    assert reads(server, TRANSITIONS) == 1


def test_a_cached_list_without_the_wanted_status_is_read_live():
    cache = DictMetadataCache()
    cache.store_transitions(
        "SEC", ISSUE_TYPE, "To Do", [transition("11", "In Progress")]
    )
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("31", "In Review")])

        make_tracker(server, metadata_cache=cache).set_status("SEC-7", "In Review")

    assert [p.body for p in sent(server, DO_TRANSITION)] == [
        {"transition": {"id": "31"}}
    ]


def test_a_cached_transition_cannot_close_a_ticket_either():
    cache = DictMetadataCache()
    cache.store_transitions(
        "SEC", ISSUE_TYPE, "To Do", [transition("51", "Closed", category="done")]
    )
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("51", "Closed", category="done")])

        with pytest.raises(TrackerError, match="done"):
            make_tracker(server, metadata_cache=cache).set_status("SEC-7", "Closed")

    assert sent(server, DO_TRANSITION) == []


def test_the_cache_keeps_only_the_id_and_the_target_of_each_transition():
    cache = DictMetadataCache()
    live = transition("31", "In Review")
    live["name"] = "A long name"
    live["fields"] = {"anything": "else"}
    with StubHttpServer() as server:
        serve_status(server, "To Do", [live])

        make_tracker(server, metadata_cache=cache).set_status("SEC-7", "In Review")

    assert cache.moves[("SEC", ISSUE_TYPE, "To Do")] == [
        {
            "id": "31",
            "to": {"name": "In Review", "statusCategory": {"key": "indeterminate"}},
        }
    ]
