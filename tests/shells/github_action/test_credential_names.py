import pytest

from tests.shells.github_action.support import APP_KEY, JIRA_TOKEN


def settings_with(world, **names):
    world.write_settings(
        {
            "jira_site_url": "https://acme.example.invalid",
            "jira_project_keys": ["SEC"],
            **names,
        }
    )


@pytest.mark.parametrize(
    "name",
    [
        "GOZU_APP_PRIVATE_KEY",
        "GOZU_APP_ID",
        "GITHUB_TOKEN",
        "ACTIONS_RUNTIME_TOKEN",
        "RUNNER_TEMP",
        "INPUT_ANYTHING",
    ],
)
def test_a_setting_cannot_point_a_credential_at_a_variable_of_the_action_or_the_runner(
    world, name
):
    settings_with(world, jira_token_env=name)
    world.environ["GITHUB_TOKEN"] = "x" * 20
    world.environ["ACTIONS_RUNTIME_TOKEN"] = "y" * 20
    world.environ["RUNNER_TEMP"] = "/tmp/runner"
    world.environ["INPUT_ANYTHING"] = "z" * 20

    code, spy, source = world.run_action()

    assert code == 1
    assert (spy.contexts, source.minted, world.jira.seen) == ([], [], [])
    assert "jira_token_env" in world.out.getvalue()
    assert APP_KEY not in world.out.getvalue()


def test_two_credentials_cannot_share_one_variable(world):
    settings_with(world, openai_key_env="JIRA_API_TOKEN")

    code, spy, _ = world.run_action()

    assert code == 1
    assert spy.contexts == []
    assert JIRA_TOKEN not in world.out.getvalue()


@pytest.mark.parametrize("name", ["JIRA_API_TOKEN", "OPENAI_API_KEY"])
def test_a_missing_credential_stops_the_run_and_names_the_variable(world, name):
    del world.environ[name]

    code, spy, source = world.run_action()

    assert code == 1
    assert name in world.out.getvalue()
    assert (spy.contexts, source.minted) == ([], [])


@pytest.mark.parametrize("value", ["", "   ", "abc123x"])
def test_an_empty_or_short_credential_stops_the_run_and_never_shows_the_value(
    world, value
):
    world.environ["OPENAI_API_KEY"] = value

    code, spy, _ = world.run_action()

    assert code == 1
    assert "OPENAI_API_KEY" in world.out.getvalue()
    assert spy.contexts == []
    if value.strip():
        assert value not in world.out.getvalue()


def test_a_missing_email_means_a_bearer_token(world):
    del world.environ["JIRA_EMAIL"]

    class Caller:
        def __init__(self, inner):
            self.inner = inner

        def __call__(self, context):
            context.tracker.open_tickets()
            return self.inner(context)

    from tests.shells.github_action.support import SpyRun

    code, _, _ = world.run_action(run=Caller(SpyRun(world.out)))

    assert code == 0
    assert {r.authorization for r in world.jira.seen} == {f"Bearer {JIRA_TOKEN}"}
