from typing import Any, get_origin

from veil.engine.config.meta import setting_meta
from veil.engine.constants.catalog_text import (
    CATALOG_COLUMNS,
    CATALOG_EMPTY_LIST,
    CATALOG_EMPTY_TEXT,
    CATALOG_INTRO,
    CATALOG_NO_BOUND,
    CATALOG_RULES,
    CATALOG_RULES_TITLE,
    CATALOG_TITLE,
)
from veil.engine.constants.settings_rules import ValueType
from veil.engine.models.config.catalog_entry import CatalogEntry
from veil.engine.models.config.settings import Settings


def settings_catalog() -> list[CatalogEntry]:
    """Every setting with its default, minimum, maximum, rule for a repo, reader and cache lifetime."""
    entries = []
    for key, field in Settings.model_fields.items():
        meta = setting_meta(key)
        entries.append(
            CatalogEntry(
                key=key,
                value_type=_value_type(field.annotation),
                default=field.get_default(call_default_factory=True),
                minimum=_bound(field.metadata, "ge"),
                maximum=_bound(field.metadata, "le"),
                repo_rule=meta.tighten,
                read_by=meta.reader,
            )
        )
    return entries


def render_settings_catalog() -> str:
    """The catalog as a Markdown file. The same text comes out each time."""
    header = "| " + " | ".join(CATALOG_COLUMNS) + " |"
    divider = "| " + " | ".join("---" for _ in CATALOG_COLUMNS) + " |"
    rows = [
        f"| `{e.key}` | {e.value_type} | {_show(e.default)} | {_show_bound(e.minimum)} | "
        f"{_show_bound(e.maximum)} | {e.repo_rule} | {e.read_by} |"
        for e in settings_catalog()
    ]
    rules = [f"- `{rule}`: {words}" for rule, words in CATALOG_RULES.items()]
    return (
        "\n".join(
            [CATALOG_TITLE, "", CATALOG_INTRO, "", header, divider, *rows, ""]
            + [CATALOG_RULES_TITLE, "", *rules]
        )
        + "\n"
    )


def _value_type(annotation: Any) -> ValueType:
    kinds: dict[Any, ValueType] = {
        bool: "bool",
        int: "int",
        str: "str",
        tuple: "list",
        dict: "map",
    }
    return kinds[get_origin(annotation) or annotation]


def _bound(metadata: list[Any], name: str) -> int | None:
    for item in metadata:
        if hasattr(item, name):
            return getattr(item, name)
    return None


def _show_bound(value: int | None) -> str:
    return CATALOG_NO_BOUND if value is None else str(value)


def _show(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return ", ".join(f"{word}={bucket}" for word, bucket in value.items())
    if isinstance(value, tuple | list):
        return ", ".join(value) if value else CATALOG_EMPTY_LIST
    if value == "":
        return CATALOG_EMPTY_TEXT
    return str(value)
