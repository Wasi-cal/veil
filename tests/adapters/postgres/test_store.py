import pytest

from tests.support.postgres_sql import read, run
from tests.support.scenario import CHEAP, STRONG, make_context, toggle_edits
from veil.adapters.postgres.store import PostgresSettingsStore
from veil.engine import Settings, SettingsError
from veil.engine import run as run_engine

ACTOR = "alice"


@pytest.fixture
def store(engine):
    return PostgresSettingsStore(engine)


def audit(engine, actor=ACTOR):
    return read(
        engine,
        "SELECT action, scope, key, old_value, new_value FROM settings_audit WHERE actor = :actor ORDER BY id",
        actor=actor,
    )


def test_a_new_database_gives_the_code_defaults(store):
    snapshot = store.read_snapshot()

    assert snapshot.settings_for() == Settings()


def test_an_org_change_is_in_the_next_snapshot_and_in_the_audit_trail(store, engine):
    store.set_org("step_cap", 40, actor=ACTOR)

    assert store.read_snapshot().settings_for().step_cap == 40
    assert audit(engine) == [("update", "org", "step_cap", 25, 40)]


@pytest.mark.parametrize(
    ("key", "value", "words"),
    [
        ("step_cap", 0, "org settings: step_cap must be at least 1."),
        ("step_cap", 101, "org settings: step_cap must be at most 100."),
        ("step_cap", "many", "org settings: step_cap must be a whole number."),
        ("no_such_setting", 1, "org settings: unknown setting no_such_setting."),
    ],
)
def test_the_store_checks_a_value_with_the_schema_and_changes_nothing_when_it_fails(
    store, engine, key, value, words
):
    with pytest.raises(SettingsError) as error:
        store.set_org(key, value, actor=ACTOR)

    assert words in str(error.value)
    assert audit(engine) == []
    assert store.read_snapshot().settings_for() == Settings()


def test_the_store_refuses_a_value_that_looks_like_a_secret(store, engine):
    token = "".join(["gh", "p_", "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0"])  # noqa: FLY002

    with pytest.raises(SettingsError) as error:
        store.set_org("cheap_model", token, actor=ACTOR)

    assert token not in str(error.value)
    assert audit(engine) == []


def test_a_repo_row_is_a_layer_for_that_repo_only(store):
    store.set_org("step_cap", 40, actor=ACTOR)
    store.set_repo("acme/app", "step_cap", 10, actor=ACTOR)

    snapshot = store.read_snapshot(["acme/app", "acme/other"])

    assert snapshot.settings_for("acme/app").step_cap == 10
    assert snapshot.settings_for("acme/other").step_cap == 40
    assert snapshot.settings_for().step_cap == 40


def test_a_repo_can_only_tighten_an_org_value(store, engine):
    store.set_org("step_cap", 40, actor=ACTOR)

    with pytest.raises(SettingsError) as error:
        store.set_repo("acme/app", "step_cap", 60, actor=ACTOR)

    assert "repo settings: step_cap is higher than the org value." in str(error.value)
    assert audit(engine)[-1][:3] == ("update", "org", "step_cap")
    assert store.read_snapshot(["acme/app"]).settings_for("acme/app").step_cap == 40


def test_a_repo_can_never_change_a_locked_value_such_as_the_jira_site(store):
    with pytest.raises(SettingsError, match="jira_site_url is set by the org"):
        store.set_repo(
            "acme/app", "jira_site_url", "https://evil.example.com", actor=ACTOR
        )


def test_a_repo_can_choose_its_own_model(store):
    store.set_repo("acme/app", "cheap_model", "repo-model", actor=ACTOR)

    snapshot = store.read_snapshot(["acme/app"])

    assert snapshot.settings_for("acme/app").cheap_model == "repo-model"
    assert snapshot.settings_for().cheap_model == Settings().cheap_model


def test_clearing_a_repo_row_gives_the_org_value_back_and_is_audited(store, engine):
    store.set_repo("acme/app", "step_cap", 10, actor=ACTOR)

    store.clear_repo("acme/app", "step_cap", actor=ACTOR)

    assert store.read_snapshot(["acme/app"]).settings_for("acme/app").step_cap == 25
    assert [row[0] for row in audit(engine)] == ["insert", "delete"]


def test_a_setting_with_no_org_row_gets_its_code_default(store, engine):
    run(
        engine,
        "DELETE FROM settings WHERE scope = 'org' AND key = 'step_cap'",
        actor="admin",
        migrating=True,
    )

    assert store.read_snapshot().settings_for().step_cap == Settings().step_cap


def test_a_snapshot_never_changes_and_the_next_snapshot_sees_the_change(store):
    first = store.read_snapshot()

    store.set_org("step_cap", 40, actor=ACTOR)
    second = store.read_snapshot()

    assert first.settings_for().step_cap == 25
    assert second.settings_for().step_cap == 40
    assert second.version > first.version


def test_a_snapshot_is_plain_data_that_a_workflow_can_carry(store):
    store.set_repo("acme/app", "step_cap", 10, actor=ACTOR)
    snapshot = store.read_snapshot(["acme/app"])

    again = type(snapshot).model_validate_json(snapshot.model_dump_json())

    assert again == snapshot
    assert again.settings_for("acme/app").step_cap == 10


def test_a_repo_that_the_snapshot_did_not_read_is_an_error_and_not_a_silent_org_value(
    store,
):
    snapshot = store.read_snapshot(["acme/app"])

    with pytest.raises(KeyError, match="acme/other"):
        snapshot.settings_for("acme/other")


def test_per_run_overrides_apply_after_the_database_layers(store):
    store.set_org("step_cap", 40, actor=ACTOR)
    snapshot = store.read_snapshot()

    assert snapshot.settings_for(overrides={"step_cap": 5}).step_cap == 5


def test_the_engine_runs_with_a_limit_that_came_from_the_database(store, tmp_path):
    store.set_repo("acme/app", "step_cap", 2, actor=ACTOR)
    settings = store.read_snapshot(["acme/app"]).settings_for("acme/app")
    context, _, _, _ = make_context(
        tmp_path, {CHEAP: toggle_edits(5), STRONG: toggle_edits(5)}, settings=settings
    )

    report = run_engine(context)

    assert report.outcomes == {"GR-100": "failed"}


def test_changing_an_org_value_that_would_loosen_a_repo_row_is_refused_and_names_the_repo(
    store,
):
    store.set_org("step_cap", 40, actor=ACTOR)
    store.set_repo("acme/app", "step_cap", 35, actor=ACTOR)

    with pytest.raises(SettingsError) as error:
        store.set_org("step_cap", 20, actor=ACTOR)

    assert (
        "the new value of step_cap would loosen the value of the repo acme/app"
        in str(error.value)
    )
    assert store.read_snapshot().settings_for().step_cap == 40


def test_a_locked_org_value_cannot_change_under_a_repo_row_that_differs(store):
    store.set_repo("acme/app", "cheap_model", "repo-model", actor=ACTOR)
    store.set_org("cheap_model", "other-model", actor=ACTOR)

    snapshot = store.read_snapshot(["acme/app"])

    assert snapshot.settings_for("acme/app").cheap_model == "repo-model"


@pytest.mark.parametrize(
    ("key", "value", "words"),
    [
        ("step_cap", "2", "org settings: step_cap must be a whole number."),
        ("step_cap", 2.0, "org settings: step_cap must be a whole number."),
        (
            "schedule_enabled",
            "true",
            "org settings: schedule_enabled must be true or false.",
        ),
        ("repos_allow", "acme/app", "org settings: repos_allow must be a list."),
        ("cheap_model", 5, "org settings: cheap_model must be text."),
    ],
)
def test_the_store_keeps_the_exact_json_kind_of_a_setting_and_says_so(
    store, key, value, words
):
    with pytest.raises(SettingsError) as error:
        store.set_org(key, value, actor=ACTOR)

    assert words in str(error.value)


def test_a_missing_org_row_is_reported_before_the_value_is_checked(store, engine):
    run(
        engine,
        "DELETE FROM settings WHERE scope = 'org' AND key = 'step_cap'",
        actor="admin",
        migrating=True,
    )

    with pytest.raises(SettingsError, match="The org row of step_cap is missing"):
        store.set_repo("acme/app", "step_cap", 9999, actor=ACTOR)


def test_an_actor_that_is_blank_is_refused_before_the_database(store):
    with pytest.raises(ValueError, match="actor"):
        store.set_org("step_cap", 30, actor="  ")


def test_a_repo_write_waits_for_a_change_of_the_org_row_that_is_in_progress(
    admin_url, engine
):
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    url = make_url(engine.url).render_as_string(hide_password=False)
    patient = create_engine(url, connect_args={"options": "-c lock_timeout=700"})
    holder = engine.connect()
    holder.execute(
        text(
            "SELECT 1 FROM settings WHERE scope = 'org' AND key = 'step_cap' FOR UPDATE"
        )
    )
    try:
        with pytest.raises(SettingsError, match="refused"):
            PostgresSettingsStore(patient).set_repo(
                "acme/app", "step_cap", 10, actor=ACTOR
            )
    finally:
        holder.rollback()
        holder.close()
        patient.dispose()
