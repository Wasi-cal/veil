from veil.engine.constants.settings_rules import TightenRule

CATALOG_TITLE = "# Settings catalog"
CATALOG_INTRO = (
    "The declaration of the settings makes this file. Do not edit it.\n"
    "Run `python docs/settings/build.py` to make it again.\n"
    "\n"
    "Each setting has a default in code. Four layers can change it. A later layer wins:\n"
    "defaults, org settings, repo settings, per-run overrides.\n"
    "Settings hold no secrets. The safety rules are code and are not settings."
)
CATALOG_COLUMNS = (
    "Key",
    "Type",
    "Default",
    "Minimum",
    "Maximum",
    "Repo rule",
    "Read by",
)
CATALOG_RULES_TITLE = "## What a repo may do with a value that the org set"
CATALOG_RULES: dict[TightenRule, str] = {
    "lower": "A repo may lower the value. It may not raise it.",
    "add_only": "A repo may add entries. It may not drop one.",
    "raise_only": "A repo may raise a severity bucket. It may not lower one.",
    "disable_only": "A repo may turn the setting off. It may not turn it on.",
    "locked": "A repo may not change the value.",
    "free": "A repo may set any value that the bounds allow.",
}
CATALOG_NO_BOUND = "-"
CATALOG_EMPTY_LIST = "(none)"
CATALOG_EMPTY_TEXT = "(empty)"
