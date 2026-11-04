import pytest

from veil.engine import Settings, SettingsError, parse_settings


def test_with_no_values_the_settings_are_the_defaults():
    assert parse_settings() == Settings()
    assert parse_settings({}) == Settings()


def test_the_values_change_only_the_settings_that_they_name():
    settings = parse_settings({"step_cap": 20, "search_max_matches": 10})

    assert (settings.step_cap, settings.search_max_matches) == (20, 10)
    assert settings.read_file_max_lines == Settings().read_file_max_lines


def test_an_unknown_setting_fails_and_the_message_names_the_key():
    with pytest.raises(SettingsError) as error:
        parse_settings({"step_capp": 5})

    assert "unknown setting step_capp." in str(error.value)


@pytest.mark.parametrize(
    "key", ["allow_workflow_edits", "allow_default_branch", "allow_merge", "shell"]
)
def test_a_safety_rule_is_not_a_setting(key):
    with pytest.raises(SettingsError, match=f"unknown setting {key}"):
        parse_settings({key: True})


@pytest.mark.parametrize(
    ("value", "words"),
    [
        ("many", "must be a whole number"),
        (0, "must be at least 1"),
        (101, "must be at most 100"),
        (2.5, "must be a whole number"),
        (True, "must be a whole number"),
    ],
)
def test_a_value_of_the_wrong_type_or_out_of_bounds_fails_with_a_clear_message(
    value, words
):
    with pytest.raises(SettingsError) as error:
        parse_settings({"step_cap": value})

    assert f"step_cap {words}." in str(error.value)


def test_every_problem_is_in_one_message():
    with pytest.raises(SettingsError) as error:
        parse_settings({"step_cap": 0, "nope": 1, "search_max_matches": "x"})

    lines = str(error.value).splitlines()
    assert len(lines) == 3
    assert any(line.startswith("step_cap") for line in lines)
    assert any(line.startswith("unknown setting nope") for line in lines)
    assert any(line.startswith("search_max_matches") for line in lines)


@pytest.mark.parametrize("values", [["not", "a", "mapping"], "text", 5])
def test_settings_that_are_not_a_mapping_fail(values):
    with pytest.raises(SettingsError, match="must be a mapping"):
        parse_settings(values)


def test_a_bad_value_never_shows_in_the_message():
    with pytest.raises(SettingsError) as error:
        parse_settings({"step_cap": "SENSITIVE-VALUE-1234"})

    assert "SENSITIVE-VALUE-1234" not in str(error.value)


def test_the_severity_map_changes_only_its_own_words():
    settings = parse_settings({"severity_map": {"info": "medium"}})

    assert settings.severity_map["INFO"] == "medium"
    assert settings.severity_map["BLOCKER"] == "high"


def test_a_severity_word_that_maps_to_no_bucket_fails():
    with pytest.raises(SettingsError, match="severity_map"):
        parse_settings({"severity_map": {"INFO": "urgent"}})


def test_the_default_values_hold_in_the_model_itself():
    with pytest.raises(Exception, match="step_cap"):
        Settings(step_cap=0)
