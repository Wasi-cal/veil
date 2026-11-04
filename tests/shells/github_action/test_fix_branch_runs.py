import json

import pytest

from tests.shells.github_action.support import SpyRun

SETTINGS = {
    "jira_site_url": "https://acme.example.invalid",
    "jira_project_keys": ["SEC"],
    "pull_request_enabled": True,
}


def pull_request_event(world, head_branch):
    head = {"ref": head_branch, "repo": {"full_name": "acme/app"}}
    path = world.tmp_path / "event.json"
    path.write_text(json.dumps({"pull_request": {"head": head}}))
    return {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_EVENT_PATH": str(path)}


def without_secrets(world):
    for name in ("JIRA_API_TOKEN", "OPENAI_API_KEY", "GITHUB_TOKEN"):
        del world.environ[name]


@pytest.mark.parametrize("head", ["gozu/fix-vt-46", "gozu/fix-shared-gr-3"])
def test_a_pull_request_on_a_fix_branch_never_runs_veil(world, head):
    world.write_settings(SETTINGS)
    without_secrets(world)

    code, spy = world.run_action(**pull_request_event(world, head))

    assert (code, spy.contexts) == (0, [])
    assert "Fix branch" in world.out.getvalue()
    assert world.jira.seen == []


def test_the_prefix_setting_decides_which_branches_are_fix_branches(world):
    world.write_settings({**SETTINGS, "branch_prefix": "veil/"})
    without_secrets(world)

    code, spy = world.run_action(**pull_request_event(world, "veil/gr-7"))

    assert (code, spy.contexts) == (0, [])
    assert "Fix branch" in world.out.getvalue()


def test_a_pull_request_on_the_default_prefix_is_refused_even_with_another_prefix(
    world,
):
    world.write_settings({**SETTINGS, "branch_prefix": "veil/"})
    without_secrets(world)

    code, spy = world.run_action(**pull_request_event(world, "gozu/fix-vt-46"))

    assert (code, spy.contexts) == (0, [])


def test_a_pull_request_on_a_normal_branch_still_runs(world):
    world.write_settings(SETTINGS)

    code, spy = world.run_action(**pull_request_event(world, "veil-test"))

    assert (code, len(spy.contexts)) == (0, 1)


@pytest.mark.parametrize(
    "event", ["workflow_dispatch", "schedule", "repository_dispatch"]
)
def test_a_run_started_on_a_fix_branch_by_any_event_is_refused(world, event):
    world.write_settings({**SETTINGS, "schedule_enabled": True})
    without_secrets(world)

    code, spy = world.run_action(
        GITHUB_EVENT_NAME=event, GITHUB_REF_NAME="gozu/fix-vt-46"
    )

    assert (code, spy.contexts) == (0, [])
    assert "Fix branch" in world.out.getvalue()
    assert world.jira.seen == []


def test_a_run_started_on_a_normal_branch_still_runs(world):
    code, spy = world.run_action(GITHUB_REF_NAME="main")

    assert (code, len(spy.contexts)) == (0, 1)


def test_a_run_without_a_branch_name_still_runs(world):
    code, spy = world.run_action()

    assert (code, len(spy.contexts)) == (0, 1)
    assert isinstance(spy, SpyRun)
