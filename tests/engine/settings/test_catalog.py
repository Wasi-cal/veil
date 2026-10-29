from pathlib import Path
from typing import get_args

from veil.engine import Settings, render_settings_catalog, settings_catalog
from veil.engine.constants.settings_rules import Reader, TightenRule

ROOT = Path(__file__).resolve().parents[3]
CATALOG_FILE = ROOT / "docs" / "settings-catalog.md"


def entry(key):
    return next(e for e in settings_catalog() if e.key == key)


def test_the_catalog_lists_every_setting_once():
    keys = [e.key for e in settings_catalog()]

    assert keys == list(Settings.model_fields)
    assert len(set(keys)) == len(keys)


def test_a_number_has_its_default_its_minimum_and_its_maximum():
    step_cap = entry("step_cap")

    assert (step_cap.default, step_cap.minimum, step_cap.maximum) == (25, 1, 100)
    diff = entry("diff_limit")
    assert (diff.default, diff.minimum, diff.maximum) == (200, 0, 2000)
    ceiling = entry("token_ceiling")
    assert (ceiling.default, ceiling.minimum, ceiling.maximum) == (
        100_000,
        1,
        5_000_000,
    )


def test_a_name_has_a_default_and_no_bounds():
    model = entry("cheap_model")

    assert model.default == "gpt-6-luna"
    assert (model.minimum, model.maximum) == (None, None)


def test_every_setting_says_what_a_repo_may_do_and_who_reads_it():
    for item in settings_catalog():
        assert item.repo_rule in get_args(TightenRule)
        assert item.read_by in get_args(Reader)
    assert entry("step_cap").repo_rule == "lower"
    assert entry("branch_prefix").repo_rule == "locked"
    assert entry("model_calls_per_minute").read_by == "shell"


def test_the_catalog_file_explains_every_rule():
    text = render_settings_catalog()

    for rule in get_args(TightenRule):
        assert f"- `{rule}`:" in text


def test_every_setting_names_the_setting_that_holds_its_cache_lifetime():
    assert {e.cache_lifetime for e in settings_catalog()} == {
        "cache_settings_ttl_seconds"
    }


def test_the_rendered_table_has_one_row_for_each_setting():
    text = render_settings_catalog()

    for key in Settings.model_fields:
        assert f"| `{key}` |" in text
    assert "| `step_cap` | 25 | 1 | 100 |" in text


def test_the_catalog_file_in_docs_is_the_current_catalog():
    assert CATALOG_FILE.is_file(), "Run: python docs/settings/build.py"
    assert CATALOG_FILE.read_text() == render_settings_catalog(), (
        "The catalog file is old. Run: python docs/settings/build.py"
    )
