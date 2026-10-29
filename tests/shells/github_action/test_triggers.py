import pytest

from tests.shells.github_action.support import FakeTokenSource


@pytest.mark.parametrize(
    ("event", "setting"),
    [
        ("schedule", "schedule_enabled"),
        ("workflow_dispatch", "on_demand_enabled"),
        ("repository_dispatch", "event_enabled"),
    ],
)
def test_each_event_runs_only_when_its_trigger_is_on(world, event, setting):
    world.write_settings(
        {
            "jira_site_url": "https://acme.example.invalid",
            "jira_project_keys": ["SEC"],
            setting: True,
        }
    )
    code, spy, source = world.run_action(GITHUB_EVENT_NAME=event)
    assert (code, len(spy.contexts), source.minted) == (0, 1, ["acme/app"])

    world.write_settings(
        {
            "jira_site_url": "https://acme.example.invalid",
            "jira_project_keys": ["SEC"],
            setting: False,
        }
    )
    code, spy, source = world.run_action(
        token_source=FakeTokenSource(), GITHUB_EVENT_NAME=event
    )
    assert (code, spy.contexts, source.minted) == (0, [], [])
    assert setting in world.out.getvalue()


def test_the_schedule_trigger_is_off_by_default(world):
    code, spy, source = world.run_action(GITHUB_EVENT_NAME="schedule")

    assert (code, spy.contexts, source.minted) == (0, [], [])


@pytest.mark.parametrize(
    "event", ["pull_request", "pull_request_target", "push", "issue_comment", ""]
)
def test_any_other_event_is_refused_before_a_token_or_a_ticket_is_touched(world, event):
    code, spy, source = world.run_action(GITHUB_EVENT_NAME=event)

    assert code == 1
    assert "cannot start a run" in world.out.getvalue()
    assert spy.contexts == []
    assert source.minted == []
    assert world.jira.seen == []
