from typing import Any

from pydantic import BaseModel, ConfigDict

from veil.engine.constants.settings_rules import Reader, TightenRule, ValueType


class CatalogEntry(BaseModel):
    """One row of the settings catalog. The row comes from the declaration of the setting."""

    model_config = ConfigDict(frozen=True)

    key: str
    value_type: ValueType
    default: Any
    minimum: int | None
    maximum: int | None
    repo_rule: TightenRule
    read_by: Reader
