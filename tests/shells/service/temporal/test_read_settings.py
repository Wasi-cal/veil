from tests.shells.service.support import make_deps
from tests.shells.service.temporal.support import activity_env
from veil.adapters.postgres.store import PostgresSettingsStore
from veil.shells.service.temporal.activities import EngineActivities


def test_it_reads_the_snapshot_of_the_repo_from_the_real_database(
    tmp_path, stubs, engine
):
    store = PostgresSettingsStore(engine)
    store.set_org("step_cap", 12, actor="test")
    store.set_repo("acme/app", "diff_limit", 50, actor="test")
    activities = EngineActivities(make_deps(tmp_path, stubs, settings_source=store))
    env, _ = activity_env()

    snapshot = env.run(activities.read_settings, "acme/app")

    settings = snapshot.settings_for("acme/app")
    assert (settings.step_cap, settings.diff_limit) == (12, 50)
    assert snapshot.settings_for("acme/app") == store.read_snapshot(
        ["acme/app"]
    ).settings_for("acme/app")


def test_the_snapshot_does_not_change_when_the_database_changes_later(
    tmp_path, stubs, engine
):
    store = PostgresSettingsStore(engine)
    activities = EngineActivities(make_deps(tmp_path, stubs, settings_source=store))
    env, _ = activity_env()
    before = env.run(activities.read_settings, "acme/app")

    store.set_org("step_cap", 3, actor="test")

    assert before.settings_for("acme/app").step_cap == 25


def test_the_snapshot_holds_no_credential(tmp_path, stubs, engine):
    activities = EngineActivities(
        make_deps(tmp_path, stubs, settings_source=PostgresSettingsStore(engine))
    )
    env, _ = activity_env()

    snapshot = env.run(activities.read_settings, "acme/app")

    from tests.shells.github_action.support import JIRA_TOKEN, OPENAI_KEY

    text = snapshot.model_dump_json()
    assert JIRA_TOKEN not in text and OPENAI_KEY not in text
