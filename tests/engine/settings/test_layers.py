import pytest

from veil.engine import Settings, SettingsError, resolve_settings


def test_with_no_layers_the_settings_are_the_defaults():
    assert resolve_settings() == Settings()


def test_a_later_layer_wins_over_an_earlier_one():
    org = {"cheap_model": "org-model"}
    repo = {"cheap_model": "repo-model"}
    overrides = {"cheap_model": "run-model"}

    assert resolve_settings(org=org).cheap_model == "org-model"
    assert resolve_settings(org=org, repo=repo).cheap_model == "repo-model"
    assert (
        resolve_settings(org=org, repo=repo, overrides=overrides).cheap_model
        == "run-model"
    )


def test_a_layer_changes_only_the_settings_that_it_names():
    settings = resolve_settings(org={"step_cap": 20}, repo={"diff_limit": 100})

    assert (settings.step_cap, settings.diff_limit) == (20, 100)
    assert settings.read_file_max_lines == Settings().read_file_max_lines


def test_an_unknown_setting_fails_and_the_message_names_the_layer_and_the_key():
    with pytest.raises(SettingsError) as error:
        resolve_settings(repo={"step_capp": 5})

    assert "repo settings: unknown setting step_capp." in str(error.value)


@pytest.mark.parametrize(
    "key", ["allow_workflow_edits", "allow_default_branch", "allow_merge", "shell"]
)
def test_a_safety_rule_is_not_a_setting(key):
    with pytest.raises(SettingsError, match=f"unknown setting {key}"):
        resolve_settings(org={key: True})


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
        resolve_settings(org={"step_cap": value})

    assert f"org settings: step_cap {words}." in str(error.value)


def test_every_problem_of_every_layer_is_in_one_message():
    with pytest.raises(SettingsError) as error:
        resolve_settings(
            org={"step_cap": 0, "nope": 1},
            repo={"diff_limit": "x"},
            overrides=["not", "a", "mapping"],
        )

    lines = str(error.value).splitlines()
    assert len(lines) == 4
    assert any(line.startswith("org settings: step_cap") for line in lines)
    assert any(line.startswith("org settings: unknown setting nope") for line in lines)
    assert any(line.startswith("repo settings: diff_limit") for line in lines)
    assert any("overrides must be a mapping" in line for line in lines)


def test_a_bad_value_never_shows_in_the_message():
    with pytest.raises(SettingsError) as error:
        resolve_settings(org={"step_cap": "SENSITIVE-VALUE-1234"})

    assert "SENSITIVE-VALUE-1234" not in str(error.value)


def test_the_severity_map_of_a_layer_changes_only_its_own_words():
    settings = resolve_settings(org={"severity_map": {"info": "medium"}})

    assert settings.severity_map["INFO"] == "medium"
    assert settings.severity_map["BLOCKER"] == "high"


def test_a_severity_word_that_maps_to_no_bucket_fails():
    with pytest.raises(SettingsError, match="severity_map"):
        resolve_settings(org={"severity_map": {"INFO": "urgent"}})
