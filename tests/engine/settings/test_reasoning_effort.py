import pytest

from tests.support.scenario import EDIT_THEN_FINISH, make_context, toggle_edits
from veil.engine import Settings, SettingsError, parse_settings, run


def test_the_effort_is_not_set_by_default():
    assert parse_settings({}).cheap_reasoning_effort is None


def test_a_known_effort_is_accepted():
    settings = parse_settings({"cheap_reasoning_effort": "low"})

    assert settings.cheap_reasoning_effort == "low"


@pytest.mark.parametrize("value", ["fast", "LOW", "", 3])
def test_an_unknown_effort_fails_the_settings_before_any_ticket(value):
    with pytest.raises(SettingsError):
        parse_settings({"cheap_reasoning_effort": value})


def test_the_cheap_attempt_asks_for_the_effort_and_the_strong_attempt_does_not(
    tmp_path,
):
    context, _, _, model = make_context(
        tmp_path,
        {"small": toggle_edits(2), "big": EDIT_THEN_FINISH},
        settings=Settings(
            step_cap=2,
            cheap_model="small",
            strong_model="big",
            cheap_reasoning_effort="low",
        ),
    )

    run(context)

    assert model.models_used == ["small", "small", "big", "big"]
    assert model.efforts_used == ["low", "low", None, None]


def test_without_the_setting_no_call_asks_for_an_effort(tmp_path):
    context, _, _, model = make_context(tmp_path, EDIT_THEN_FINISH)

    run(context)

    assert set(model.efforts_used) == {None}
