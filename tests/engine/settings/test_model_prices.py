import pytest

from veil.engine import SettingsError, parse_settings
from veil.engine.fix.cost import price_table


def test_the_default_prices_cover_the_default_models():
    settings = parse_settings({})

    table = price_table(settings)

    assert table[settings.cheap_model].output < table[settings.strong_model].output


def test_a_price_in_the_settings_adds_a_model_and_replaces_a_default():
    settings = parse_settings(
        {
            "model_prices": {
                "my-model": {"input": 1, "cached_input": 0.1, "output": 2},
                "gpt-6-luna": {"input": 9, "cached_input": 9, "output": 9},
            }
        }
    )

    table = price_table(settings)

    assert table["my-model"].output == 2
    assert table["gpt-6-luna"].input == 9


@pytest.mark.parametrize(
    "price",
    [
        {"input": -1, "cached_input": 0, "output": 1},
        {"input": 1, "cached_input": 0},
        {"input": 1, "cached_input": 0, "output": 1, "extra": 1},
    ],
)
def test_a_wrong_price_fails_the_settings_before_any_ticket(price):
    with pytest.raises(SettingsError):
        parse_settings({"model_prices": {"my-model": price}})
