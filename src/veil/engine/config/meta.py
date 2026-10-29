from veil.engine.models.config.setting_meta import SettingMeta
from veil.engine.models.config.settings import Settings


def setting_meta(key: str) -> SettingMeta:
    """The rule for a repo and the reader of a setting. Both are declared with the setting."""
    extra = Settings.model_fields[key].json_schema_extra
    if not isinstance(extra, dict):
        raise TypeError(f"The setting {key} has no rule.")
    return SettingMeta.model_validate(extra)
