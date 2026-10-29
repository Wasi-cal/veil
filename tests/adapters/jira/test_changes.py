import pytest

from tests.adapters.jira.support import make_tracker
from tests.fakes.http_server import StubHttpServer
from veil.engine.errors.tracker_error import TrackerError

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
    server.routes[ISSUE] = (200, {"fields": {"status": {"name": current}}})
    server.routes[TRANSITIONS] = (200, {"transitions": transitions or []})
    server.routes[DO_TRANSITION] = (204, None)


def sent(server: StubHttpServer, route: tuple[str, str]):
    return [r for r in server.seen if (r.method, r.path) == route]


def test_add_label_asks_jira_to_add_the_label_without_a_read_first():
    with StubHttpServer() as server:
        server.routes[EDIT] = (204, None)

        make_tracker(server).add_label("SEC-7", "veil-failed-fix")
        make_tracker(server).add_label("SEC-7", "veil-failed-fix")

    bodies = [r.body for r in sent(server, EDIT)]
    assert bodies == [{"update": {"labels": [{"add": "veil-failed-fix"}]}}] * 2
    assert {r.method for r in server.seen} == {"PUT"}


def test_set_status_makes_the_transition_that_ends_in_that_status():
    with StubHttpServer() as server:
        serve_status(
            server,
            "To Do",
            [transition("11", "In Progress"), transition("31", "In Review")],
        )

        make_tracker(server).set_status("SEC-7", "In Review")

    [post] = sent(server, DO_TRANSITION)
    assert post.body == {"transition": {"id": "31"}}


def test_set_status_does_nothing_when_the_ticket_is_already_in_that_status():
    with StubHttpServer() as server:
        serve_status(server, "In Review", [transition("31", "In Review")])

        make_tracker(server).set_status("SEC-7", "In Review")

    assert sent(server, DO_TRANSITION) == []


def test_the_adapter_never_closes_a_ticket():
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("51", "Closed", category="done")])

        with pytest.raises(TrackerError, match="done"):
            make_tracker(server).set_status("SEC-7", "Closed")

    assert sent(server, DO_TRANSITION) == []


def test_a_status_that_the_workflow_does_not_offer_is_an_error():
    with StubHttpServer() as server:
        serve_status(server, "To Do", [transition("11", "In Progress")])

        with pytest.raises(TrackerError, match="In Review"):
            make_tracker(server).set_status("SEC-7", "In Review")

    assert sent(server, DO_TRANSITION) == []


@pytest.mark.parametrize("key", ["../admin", "SEC-7/transitions", "sec-7", ""])
def test_a_key_that_is_not_a_ticket_key_is_refused_before_any_request(key):
    with StubHttpServer() as server:
        tracker = make_tracker(server)

        with pytest.raises(TrackerError):
            tracker.add_label(key, "veil-failed-fix")
        with pytest.raises(TrackerError):
            tracker.set_status(key, "In Review")

    assert server.seen == []


@pytest.mark.parametrize("label", ["two words", 'quote"', ""])
def test_a_label_that_jira_cannot_hold_is_refused(label):
    with StubHttpServer() as server, pytest.raises(TrackerError):
        make_tracker(server).add_label("SEC-7", label)

    assert server.seen == []
