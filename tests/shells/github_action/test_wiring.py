import base64

from tests.adapters.github.support import TOKEN
from tests.shells.github_action.support import (
    JIRA_EMAIL,
    JIRA_TOKEN,
    OPENAI_KEY,
    FakeTokenSource,
    SpyRun,
)


def test_it_runs_the_engine_once_with_the_repo_settings_and_the_minted_token(world):
    world.write_settings(
        {
            "jira_site_url": "https://acme.example.invalid",
            "jira_project_keys": ["SEC"],
            "token_ceiling": 5000,
        }
    )

    code, spy, source = world.run_action()

    assert code == 0
    assert source.minted == ["acme/app"]
    [context] = spy.contexts
    assert context.settings.token_ceiling == 5000
    assert context.settings.jira_project_keys == ("SEC",)
    assert set(context.credential_values) == {TOKEN, JIRA_TOKEN, OPENAI_KEY}


def test_defaults_apply_when_the_repo_has_no_settings_file_except_the_jira_site(world):
    (world.workspace / ".gozu" / "jira-to-pr.yml").unlink()

    code, spy, _ = world.run_action()

    assert code == 1
    assert spy.contexts == []
    assert "jira_site_url" in world.out.getvalue()


def test_the_tracker_logs_in_with_the_jira_email_and_token_from_the_environment(world):
    class Caller(SpyRun):
        def __call__(self, context):
            context.tracker.open_tickets()
            return super().__call__(context)

    caller = Caller(world.out)
    code, _, _ = world.run_action(run=caller)

    assert code == 0
    basic = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    assert {r.authorization for r in world.jira.seen} == {f"Basic {basic}"}


def test_the_repo_provider_uses_the_minted_token_and_asks_only_about_this_repo(world):
    world.github.routes[("GET", "/repos/acme/app/pulls")] = (200, [])

    class Caller(SpyRun):
        def __call__(self, context):
            context.repo_provider.has_open_pr("acme/app", "feature-x")
            return super().__call__(context)

    code, _, _ = world.run_action(run=Caller(world.out))

    assert code == 0
    assert {r.authorization for r in world.github.seen} == {f"Bearer {TOKEN}"}
    assert {r.path for r in world.github.seen} == {"/repos/acme/app/pulls"}


def test_the_settings_can_name_other_variables_for_the_credentials(world):
    world.write_settings(
        {
            "jira_site_url": "https://acme.example.invalid",
            "jira_project_keys": ["SEC"],
            "jira_token_env": "ACME_JIRA_TOKEN",
            "jira_email_env": "ACME_JIRA_USER",
            "openai_key_env": "ACME_OPENAI_KEY",
        }
    )
    for name in ("JIRA_API_TOKEN", "JIRA_EMAIL", "OPENAI_API_KEY"):
        del world.environ[name]
    world.environ["ACME_JIRA_TOKEN"] = JIRA_TOKEN
    world.environ["ACME_JIRA_USER"] = JIRA_EMAIL
    world.environ["ACME_OPENAI_KEY"] = OPENAI_KEY

    code, spy, _ = world.run_action(token_source=FakeTokenSource())

    assert code == 0
    assert set(spy.contexts[0].credential_values) == {TOKEN, JIRA_TOKEN, OPENAI_KEY}
