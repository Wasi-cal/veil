from typing import Literal

# What a repo may do with a value that the org set. A repo can only make the value tighter.
TightenRule = Literal[
    "lower", "add_only", "raise_only", "disable_only", "locked", "free"
]
# Who reads a setting. The settings catalog shows it.
Reader = Literal["engine", "shell"]

TIGHTEN_LOWER: TightenRule = "lower"
TIGHTEN_ADD_ONLY: TightenRule = "add_only"
TIGHTEN_RAISE_ONLY: TightenRule = "raise_only"
TIGHTEN_DISABLE_ONLY: TightenRule = "disable_only"
TIGHTEN_LOCKED: TightenRule = "locked"
TIGHTEN_FREE: TightenRule = "free"

READER_ENGINE: Reader = "engine"
READER_SHELL: Reader = "shell"

# The setting that holds how long a Shell may keep a snapshot of the settings in its cache.
CACHE_LIFETIME_SETTING = "cache_settings_ttl_seconds"
