from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from veil.engine.config.keys import describe_key
from veil.engine.constants.settings_text import (
    MUST_BE_WHOLE_NUMBER,
    NO_SECRETS,
    SETTINGS_NOT_A_MAPPING,
    VALUE_NOT_VALID,
    WORDS_BY_ERROR_TYPE,
)
from veil.engine.errors.settings_error import SettingsError
from veil.engine.models.config.settings import Settings, secret_kind_in


def parse_settings(values: Mapping[str, Any] | None = None) -> Settings:
    """Check the settings of one run and return them. No value means the defaults.

    Raise SettingsError, with every problem, before any ticket is touched.
    A message never holds a value. The Engine reads no file and no environment.
    The caller gives a plain mapping. The Action reads it from the repo file.
    """
    if values is None:
        return Settings()
    if not isinstance(values, Mapping):
        raise SettingsError([SETTINGS_NOT_A_MAPPING])
    problems: list[str] = []
    checked: dict[str, Any] = {}
    for key, value in values.items():
        if _is_valid(key, value, problems):
            checked[key] = value
    if problems:
        raise SettingsError(problems)
    return Settings.model_validate(checked)


def _is_valid(key: str, value: Any, problems: list[str]) -> bool:
    if key not in Settings.model_fields:
        name = describe_key(key)
        problems.append(
            f"unknown setting {key}." if name == key else f"{name} is not a setting."
        )
        return False
    kind = secret_kind_in(value)
    if kind:
        problems.append(
            f"{key} holds text that looks like a secret ({kind}). {NO_SECRETS}"
        )
        return False
    if isinstance(value, bool) and _is_number(key):
        problems.append(f"{key} {MUST_BE_WHOLE_NUMBER}.")
        return False
    try:
        Settings.model_validate({key: value})
    except ValidationError as failure:
        for detail in failure.errors():
            problems.append(f"{key} {_words(detail)}.")
        return False
    return True


def _is_number(key: str) -> bool:
    return Settings.model_fields[key].annotation is int


def _words(detail: Any) -> str:
    """What is wrong, in words. The words never hold the value."""
    kind = detail["type"]
    context = detail.get("ctx", {})
    if kind == "greater_than_equal":
        return f"must be at least {context['ge']}"
    if kind == "less_than_equal":
        return f"must be at most {context['le']}"
    return WORDS_BY_ERROR_TYPE.get(kind, VALUE_NOT_VALID)
