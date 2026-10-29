from typing import Any

from veil.engine.constants.secrets import SECRET_PATTERNS
from veil.engine.constants.settings_messages import (
    KEY_LOOKS_LIKE_SECRET,
    KEY_NOT_TEXT,
    KEY_TOO_LONG,
    MAX_KEY_CHARS_IN_MESSAGE,
)


def describe_key(key: Any) -> str:
    """The key as a message may show it. A key that is not text, is long or looks like a secret gets a description.

    A key can be a pasted secret. So a message never repeats it.
    """
    if not isinstance(key, str):
        return KEY_NOT_TEXT
    if any(pattern.search(key) for _, pattern in SECRET_PATTERNS):
        return KEY_LOOKS_LIKE_SECRET
    if len(key) > MAX_KEY_CHARS_IN_MESSAGE:
        return KEY_TOO_LONG
    return key
