from pathlib import Path
from typing import Any

import yaml

from veil.adapters.constants.settings_file import MAX_SETTINGS_FILE_BYTES
from veil.engine.config.keys import describe_key
from veil.engine.errors.settings_error import SettingsError


class _StrictLoader(yaml.SafeLoader):
    """A safe loader that also refuses a key that is not text and a key that appears twice.

    The plain safe loader keeps the last value of a repeated key. That hides a mistake.
    """

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict:
        seen: set[str] = set()
        for key_node, _ in node.value:
            line = key_node.start_mark.line + 1
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise SettingsError([f"A key on line {line} is not text."])
            if key in seen:
                raise SettingsError(
                    [f"The key {describe_key(key)} appears twice. See line {line}."]
                )
            seen.add(key)
        return super().construct_mapping(node, deep)


def load_settings_file(path: Path) -> dict[str, Any]:
    """Read the settings of one layer from a YAML file. A missing or empty file gives no settings.

    The loader runs no code. The Engine checks the settings against its schema afterwards.
    Raise SettingsError for a file that is not valid. The message never repeats the content.
    """
    if path.is_dir():
        raise SettingsError([f"The settings path {path.name} is a directory."])
    if not path.is_file():
        return {}
    if path.stat().st_size > MAX_SETTINGS_FILE_BYTES:
        raise SettingsError([f"The settings file {path.name} is too big."])
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise SettingsError([f"The settings file {path.name} is not text."]) from None
    try:
        if any(
            isinstance(e, yaml.AliasEvent) for e in yaml.parse(text, yaml.SafeLoader)
        ):
            raise SettingsError(
                [
                    f"The settings file {path.name} uses aliases. Aliases are not allowed."
                ]
            )
        loaded = yaml.load(text, Loader=_StrictLoader)
    except RecursionError:
        raise SettingsError(
            [f"The settings file {path.name} has too many levels."]
        ) from None
    except yaml.YAMLError as failure:
        mark = getattr(failure, "problem_mark", None)
        where = f" See line {mark.line + 1}." if mark else ""
        raise SettingsError(
            [f"The settings file {path.name} is not valid YAML.{where}"]
        ) from None
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise SettingsError(
            [
                f"The settings file {path.name} must hold a mapping of setting names to values."
            ]
        )
    return loaded
