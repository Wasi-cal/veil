import re

from veil.engine.constants.settings_patterns import (
    LABEL,
)
from veil.engine.constants.settings_patterns import (
    PROJECT_KEY as PROJECT_KEY_PATTERN,
)

# A Jira key is a project key, a dash and a number. It has no character that could change a URL.
ISSUE_KEY = re.compile(r"^[A-Z][A-Z0-9_]+-[0-9]+$")
# The label and the project key follow the patterns of the settings. One source for both.
SAFE_LABEL = re.compile(LABEL)
PROJECT_KEY = re.compile(PROJECT_KEY_PATTERN)
