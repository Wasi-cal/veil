from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from veil.engine.config.keys import describe_key
from veil.engine.config.meta import setting_meta
from veil.engine.constants.settings_messages import (
    LAYER_ORG,
    LAYER_OVERRIDES,
    LAYER_REPO,
    MUST_BE_WHOLE_NUMBER,
    NO_SECRETS,
    VALUE_NOT_VALID,
    WORDS_BY_ERROR_TYPE,
)
from veil.engine.constants.settings_rules import (
    TIGHTEN_ADD_ONLY,
    TIGHTEN_DISABLE_ONLY,
    TIGHTEN_LOCKED,
    TIGHTEN_LOWER,
    TIGHTEN_RAISE_ONLY,
)
from veil.engine.constants.severity import BUCKET_RANK
from veil.engine.errors.settings_error import SettingsError
from veil.engine.models.config.settings import Settings, secret_kind_in


def resolve_settings(
    org: Mapping[str, Any] | None = None,
    repo: Mapping[str, Any] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> Settings:
    """Merge the layers into the settings of one run. The order is defaults, org, repo, overrides.

    A later layer wins. A layer changes only the settings that it names.
    Raise SettingsError, with every problem of every layer, before any ticket is touched.
    The Engine reads no file and no environment. The caller gives plain mappings.
    """
    problems: list[str] = []
    merged: dict[str, Any] = {}
    org_values: dict[str, Any] = {}
    for label, layer in (
        (LAYER_ORG, org),
        (LAYER_REPO, repo),
        (LAYER_OVERRIDES, overrides),
    ):
        if layer is None:
            continue
        if not isinstance(layer, Mapping):
            problems.append(f"{label} must be a mapping of setting names to values.")
            continue
        for key, value in layer.items():
            if not _is_valid(label, key, value, problems):
                continue
            if label == LAYER_REPO and key in org_values:
                complaint = _loosens(key, org_values[key], value)
                if complaint:
                    problems.append(f"{label}: {key} {complaint}")
                    continue
            merged[key] = _merge(merged.get(key), value)
        if label == LAYER_ORG:
            org_values = dict(merged)
    if problems:
        raise SettingsError(problems)
    return Settings.model_validate(merged)


def _merge(earlier: Any, later: Any) -> Any:
    """A map from a later layer changes only its own words. Any other value is replaced."""
    if isinstance(earlier, Mapping) and isinstance(later, Mapping):
        return {**earlier, **later}
    return later


def _is_valid(label: str, key: str, value: Any, problems: list[str]) -> bool:
    if key not in Settings.model_fields:
        name = describe_key(key)
        problems.append(
            f"{label}: unknown setting {key}."
            if name == key
            else f"{label}: {name} is not a setting."
        )
        return False
    kind = secret_kind_in(value)
    if kind:
        problems.append(
            f"{label}: {key} holds text that looks like a secret ({kind}). {NO_SECRETS}"
        )
        return False
    if isinstance(value, bool) and _is_number(key):
        problems.append(f"{label}: {key} {MUST_BE_WHOLE_NUMBER}.")
        return False
    try:
        Settings.model_validate({key: value})
    except ValidationError as failure:
        for detail in failure.errors():
            problems.append(f"{label}: {key} {_words(detail)}.")
        return False
    return True


def _normalized(key: str, raw: Any) -> Any:
    return getattr(Settings.model_validate({key: raw}), key)


def _loosens(key: str, org_raw: Any, repo_raw: Any) -> str | None:
    """Say how a repo value loosens the org value, or give None. A repo can only tighten."""
    rule = setting_meta(key).tighten
    org = _normalized(key, org_raw)
    repo = _normalized(key, _merge(org_raw, repo_raw))
    if rule == TIGHTEN_LOWER and repo > org:
        return "is higher than the org value. A repo can only lower it."
    if rule == TIGHTEN_ADD_ONLY and not set(org) <= set(repo):
        return "drops a pattern of the org. A repo can only add patterns."
    if rule == TIGHTEN_RAISE_ONLY and any(
        BUCKET_RANK[repo[word]] < BUCKET_RANK[bucket] for word, bucket in org.items()
    ):
        return "lowers a bucket. A repo can only raise a bucket."
    if rule == TIGHTEN_DISABLE_ONLY and repo and not org:
        return "is off in the org. A repo can only turn it off."
    if rule == TIGHTEN_LOCKED and repo != org:
        return "is set by the org. A repo cannot change it."
    return None


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
