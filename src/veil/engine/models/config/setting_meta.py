from pydantic import BaseModel, ConfigDict

from veil.engine.constants.settings_rules import Reader, TightenRule


class SettingMeta(BaseModel):
    """What a setting declares besides its value: the rule for a repo and who reads it."""

    model_config = ConfigDict(frozen=True)

    tighten: TightenRule
    reader: Reader
