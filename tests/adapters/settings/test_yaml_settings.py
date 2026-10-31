from pathlib import Path

import pytest

from veil.adapters.yaml_settings import load_settings_file
from veil.engine import SettingsError, resolve_settings


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "jira-to-pr.yml"
    path.write_text(text)
    return path


def test_a_settings_file_gives_its_settings_as_a_mapping(tmp_path):
    path = write(
        tmp_path,
        "step_cap: 12\nextra_refused_read_patterns:\n  - '*.cfg'\nseverity_map:\n  INFO: medium\n",
    )

    assert load_settings_file(path) == {
        "step_cap": 12,
        "extra_refused_read_patterns": ["*.cfg"],
        "severity_map": {"INFO": "medium"},
    }


@pytest.mark.parametrize("text", ["", "# only a comment\n", "---\n"])
def test_an_empty_file_gives_no_settings(tmp_path, text):
    assert load_settings_file(write(tmp_path, text)) == {}


def test_a_missing_file_gives_no_settings(tmp_path):
    assert load_settings_file(tmp_path / "none.yml") == {}


def test_the_loaded_settings_are_checked_by_the_same_schema_as_any_other_layer(
    tmp_path,
):
    path = write(tmp_path, "step_cap: 12\nstep_capp: 5\ndiff_limit: 99999\n")

    with pytest.raises(SettingsError) as error:
        resolve_settings(repo=load_settings_file(path))

    lines = str(error.value).splitlines()
    assert len(lines) == 2
    assert "repo settings: unknown setting step_capp." in lines
    assert any(
        line.startswith("repo settings: diff_limit must be at most") for line in lines
    )


def test_text_that_is_not_yaml_gives_a_clear_error_with_a_line_and_no_content(tmp_path):
    path = write(tmp_path, "step_cap: [1, 2\nsecret_value_SENSITIVE: x\n")

    with pytest.raises(SettingsError) as error:
        load_settings_file(path)

    message = str(error.value)
    assert "is not valid YAML" in message
    assert "line" in message
    assert "SENSITIVE" not in message


@pytest.mark.parametrize("text", ["- a\n- b\n", "just text\n", "42\n"])
def test_a_file_that_is_not_a_mapping_is_an_error(tmp_path, text):
    with pytest.raises(SettingsError, match="must hold a mapping"):
        load_settings_file(write(tmp_path, text))


def test_a_file_cannot_make_the_loader_run_code(tmp_path):
    marker = tmp_path / "ran"
    path = write(
        tmp_path,
        f'step_cap: !!python/object/apply:os.system ["touch {marker}"]\n',
    )

    with pytest.raises(SettingsError):
        load_settings_file(path)

    assert not marker.exists()


def test_a_key_that_appears_twice_is_an_error_and_never_a_silent_last_wins(tmp_path):
    path = write(tmp_path, "step_cap: 1\ndiff_limit: 5\nstep_cap: 100\n")

    with pytest.raises(SettingsError, match="step_cap appears twice"):
        load_settings_file(path)


def test_a_key_that_is_not_text_is_an_error(tmp_path):
    with pytest.raises(SettingsError, match="not text"):
        load_settings_file(write(tmp_path, "1: x\n"))


def test_a_file_that_is_too_big_is_an_error(tmp_path):
    path = write(tmp_path, "step_cap: 1\n" + "# filler\n" * 20_000)

    with pytest.raises(SettingsError, match="too big"):
        load_settings_file(path)


def test_a_file_that_is_not_text_is_an_error(tmp_path):
    path = tmp_path / "jira-to-pr.yml"
    path.write_bytes(b"\xff\xfe\x00\x01")

    with pytest.raises(SettingsError):
        load_settings_file(path)


def test_an_alias_is_refused_because_it_can_grow_a_small_file_into_a_huge_value(
    tmp_path,
):
    path = write(tmp_path, "a: &x [1, 2]\nb: *x\n")

    with pytest.raises(SettingsError, match="aliases"):
        load_settings_file(path)


def test_a_file_with_very_deep_nesting_is_an_error_and_not_a_crash(tmp_path):
    path = write(tmp_path, "x: " + "[" * 1500 + "]" * 1500 + "\n")

    with pytest.raises(SettingsError, match="too many levels"):
        load_settings_file(path)


def test_a_path_that_is_a_directory_is_an_error(tmp_path):
    with pytest.raises(SettingsError, match="is a directory"):
        load_settings_file(tmp_path)


def test_a_repeated_key_that_is_a_secret_is_never_repeated_in_the_message(tmp_path):
    token = "".join(["gh", "p_", "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0"])  # noqa: FLY002
    path = write(tmp_path, f"{token}: 1\n{token}: 2\n")

    with pytest.raises(SettingsError) as error:
        load_settings_file(path)

    assert token not in str(error.value)
    assert "appears twice" in str(error.value)
