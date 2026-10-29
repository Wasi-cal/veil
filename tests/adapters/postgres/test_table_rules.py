import pytest
from sqlalchemy.exc import DBAPIError

from tests.support.postgres_sql import add_repo, read, run, set_org, value_of
from tests.support.secret_samples import KEY_LIKE
from veil.engine import Settings
from veil.engine.constants.secrets import SECRET_PATTERNS


def test_a_number_inside_the_bounds_is_stored(engine):
    set_org(engine, "step_cap", 30)

    assert value_of(engine, "org", "step_cap") == 30


@pytest.mark.parametrize("value", [0, 101, -5, 25.5, "many", True, None, [1]])
def test_a_number_outside_the_bounds_or_of_the_wrong_kind_is_refused(engine, value):
    with pytest.raises(DBAPIError):
        set_org(engine, "step_cap", value)

    assert value_of(engine, "org", "step_cap") == Settings().step_cap


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("schedule_enabled", "yes"),
        ("schedule_enabled", 1),
        ("cheap_model", 5),
        ("repos_allow", "acme/app"),
        ("severity_map", ["INFO"]),
    ],
)
def test_a_value_of_the_wrong_type_is_refused_for_every_kind(engine, key, value):
    with pytest.raises(DBAPIError):
        set_org(engine, key, value)


def test_a_repo_row_takes_the_type_and_the_bounds_of_the_org_row_whatever_it_says(
    engine,
):
    run(
        engine,
        "INSERT INTO settings (scope, key, value, type, min_value, max_value) "
        "VALUES ('repo:acme/app', 'step_cap', '10', 'str', 0, 999)",
    )

    [row] = read(
        engine,
        "SELECT type, min_value, max_value FROM settings WHERE scope = 'repo:acme/app'",
    )
    assert (row[0], int(row[1]), int(row[2])) == ("int", 1, 100)


def test_a_repo_row_cannot_widen_the_bounds_to_store_a_value_that_the_org_forbids(
    engine,
):
    with pytest.raises(DBAPIError):
        run(
            engine,
            "INSERT INTO settings (scope, key, value, type, min_value, max_value) "
            "VALUES ('repo:acme/app', 'step_cap', '500', 'int', 0, 999)",
        )


def test_a_repo_row_for_a_setting_that_does_not_exist_is_refused(engine):
    with pytest.raises(DBAPIError):
        add_repo(engine, "no_such_setting", "x")


@pytest.mark.parametrize("scope", ["team:acme", "repo:", "repo:acme", "repo:a b/c", ""])
def test_a_scope_that_is_not_org_or_a_repo_is_refused(engine, scope):
    with pytest.raises(DBAPIError):
        add_repo(engine, "cheap_model", "m", repo=scope)


def test_every_pattern_of_the_engine_has_a_sample_that_the_table_refuses(engine):
    for kind, pattern in SECRET_PATTERNS:
        assert any(pattern.search(sample) for sample in KEY_LIKE.values()), kind
    for sample in KEY_LIKE.values():
        with pytest.raises(DBAPIError, match="secret"):
            set_org(engine, "cheap_model", sample)
        with pytest.raises(DBAPIError, match="secret"):
            set_org(engine, "repos_allow", [f"acme/{sample}"])
    assert value_of(engine, "org", "cheap_model") == Settings().cheap_model


def test_a_value_that_only_looks_a_little_like_a_key_is_stored(engine):
    set_org(engine, "cheap_model", "gh/p-model")

    assert value_of(engine, "org", "cheap_model") == "gh/p-model"


@pytest.mark.parametrize("separator", ["\n", "\t", "\r", " "])
def test_a_secret_after_a_line_break_or_a_tab_is_still_a_secret(engine, separator):
    sample = KEY_LIKE["aws-access-key-id"]

    with pytest.raises(DBAPIError, match="secret"):
        set_org(engine, "cheap_model", f"model{separator}{sample}")


def test_a_secret_in_the_key_of_a_map_or_deep_in_a_list_is_refused(engine):
    sample = KEY_LIKE["github-token"]

    with pytest.raises(DBAPIError, match="secret"):
        set_org(engine, "severity_map", {sample: "high"})
    with pytest.raises(DBAPIError, match="secret"):
        set_org(engine, "repos_allow", ["acme/app", f"acme/{sample}"])


@pytest.mark.parametrize(
    "assignment",
    [
        "max_value = 99999",
        "min_value = -5",
        "type = 'str'",
        "key = 'other_key'",
        "scope = 'repo:acme/app'",
    ],
)
def test_the_type_the_bounds_the_key_and_the_scope_of_a_row_cannot_change_outside_a_migration(
    engine, assignment
):
    with pytest.raises(DBAPIError, match="migration"):
        run(
            engine,
            f"UPDATE settings SET {assignment} WHERE scope = 'org' AND key = 'step_cap'",
        )


def test_a_migration_may_change_the_bounds(engine):
    run(
        engine,
        "UPDATE settings SET max_value = 200 WHERE scope = 'org' AND key = 'step_cap'",
        migrating=True,
    )

    [(high,)] = read(
        engine,
        "SELECT max_value FROM settings WHERE scope = 'org' AND key = 'step_cap'",
    )
    assert int(high) == 200


def test_an_org_row_can_only_be_added_or_removed_by_a_migration(engine):
    insert = (
        "INSERT INTO settings (scope, key, value, type, min_value, max_value) "
        "VALUES ('org', 'new_setting', '1', 'int', 0, 5)"
    )
    with pytest.raises(DBAPIError, match="migration"):
        run(engine, insert)
    with pytest.raises(DBAPIError, match="migration"):
        run(engine, "DELETE FROM settings WHERE scope = 'org' AND key = 'step_cap'")

    run(engine, insert, migrating=True)

    assert value_of(engine, "org", "new_setting") == 1


def test_nobody_can_empty_the_settings_table_outside_a_migration(engine):
    with pytest.raises(DBAPIError):
        run(engine, "TRUNCATE settings")
    with pytest.raises(DBAPIError, match="actor"):
        run(engine, "TRUNCATE settings", actor=None, migrating=True)

    assert value_of(engine, "org", "step_cap") == Settings().step_cap


@pytest.mark.parametrize("actor", ["   ", "\t", "x" * 201])
def test_an_actor_that_is_blank_or_too_long_is_refused(engine, actor):
    with pytest.raises(DBAPIError, match="actor"):
        set_org(engine, "step_cap", 30, actor=actor)


@pytest.mark.parametrize("scope", ["repo:acme/*", "repo:*/app", "repo:acme/a*b"])
def test_a_repo_scope_names_one_repo_and_not_a_pattern(engine, scope):
    with pytest.raises(DBAPIError):
        add_repo(engine, "cheap_model", "m", repo=scope)
