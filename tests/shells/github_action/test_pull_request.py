import json

import pytest

from tests.fakes.jira_fixtures import gozurion_details, issue_json, search_page
from tests.shells.github_action.support import SEARCH, SpyRun

SETTINGS = {
    "jira_site_url": "https://acme.example.invalid",
    "jira_project_keys": ["SEC"],
}


def pull_request_event(world, head_repo="acme/app", head_branch="feature/login"):
    """Write the event file of the runner and return the variables that point at it."""
    head = {"ref": head_branch, "repo": {"full_name": head_repo} if head_repo else None}
    path = world.tmp_path / "event.json"
    path.write_text(json.dumps({"pull_request": {"head": head}}))
    return {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_EVENT_PATH": str(path)}


def tickets_of_two_branches(world):
    def issue(key, branch):
        return issue_json(
            key,
            labels=(f"issue-{key.lower()}", f"branch-{branch}", "veil-eligible"),
            details=gozurion_details(branch=branch),
        )

    world.jira.routes[SEARCH] = (
        200,
        search_page(
            [
                issue("SEC-1", "feature/login"),
                issue("SEC-2", "other/branch"),
                issue("SEC-3", "feature/login"),
            ]
        ),
    )


class KeysSeen(SpyRun):
    """Keep the keys of the tickets that the Engine can see."""

    def __call__(self, context):
        self.keys = [t.key for t in context.tracker.open_tickets()]
        return super().__call__(context)


def test_the_pull_request_trigger_is_off_by_default(world):
    code, spy = world.run_action(**pull_request_event(world))

    assert (code, spy.contexts) == (0, [])
    assert "pull_request_enabled" in world.out.getvalue()
    assert world.jira.seen == []


def test_a_pull_request_of_this_repo_runs_and_sees_only_the_tickets_of_its_branch(
    world,
):
    world.write_settings({**SETTINGS, "pull_request_enabled": True})
    tickets_of_two_branches(world)
    spy = KeysSeen(world.out)

    code, _ = world.run_action(run=spy, **pull_request_event(world))

    assert code == 0
    assert len(spy.contexts) == 1
    assert spy.keys == ["SEC-1", "SEC-3"]


def test_a_run_that_is_not_a_pull_request_sees_the_tickets_of_every_branch(world):
    tickets_of_two_branches(world)
    spy = KeysSeen(world.out)

    code, _ = world.run_action(run=spy)

    assert code == 0
    assert spy.keys == ["SEC-1", "SEC-2", "SEC-3"]


def test_the_name_of_the_repo_may_differ_in_case(world):
    world.write_settings({**SETTINGS, "pull_request_enabled": True})

    code, spy = world.run_action(**pull_request_event(world, head_repo="ACME/App"))

    assert (code, len(spy.contexts)) == (0, 1)


@pytest.mark.parametrize("head_repo", ["evil/app", "acme/app-fork", None])
def test_a_fork_pull_request_never_runs_and_never_needs_a_secret(world, head_repo):
    world.write_settings({**SETTINGS, "pull_request_enabled": True})
    for name in ("JIRA_API_TOKEN", "OPENAI_API_KEY", "GITHUB_TOKEN"):
        del world.environ[name]

    code, spy = world.run_action(**pull_request_event(world, head_repo=head_repo))

    assert (code, spy.contexts) == (0, [])
    assert "fork" in world.out.getvalue()
    assert world.jira.seen == []


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "not json",
        "[]",
        "{}",
        '{"pull_request": {}}',
        '{"pull_request": {"head": {}}}',
    ],
    ids=["no-file", "not-json", "not-an-object", "empty", "no-head", "no-ref"],
)
def test_a_missing_or_bad_event_file_stops_the_run_before_any_ticket_is_touched(
    world, payload
):
    world.write_settings({**SETTINGS, "pull_request_enabled": True})
    event = pull_request_event(world)
    if payload is None:
        del event["GITHUB_EVENT_PATH"]
        world.environ.pop("GITHUB_EVENT_PATH", None)
    else:
        (world.tmp_path / "event.json").write_text(payload)

    code, spy = world.run_action(**event)

    assert code == 1
    assert (
        "GITHUB_EVENT_PATH" in world.out.getvalue()
        or "event file" in world.out.getvalue()
    )
    assert spy.contexts == []
    assert world.jira.seen == []
