import re
from collections import Counter

from veil.engine.constants.secret_patterns import SECRET_PATTERNS


def _secrets_in(text: str, values: tuple[str, ...]) -> list[tuple[str, str]]:
    """Return each secret of the text as a pair: its kind and the text that matched."""
    found = []
    for value in values:
        if value:
            found += [
                ("a credential of this run", match.group())
                for match in re.finditer(re.escape(value), text)
            ]
    for kind, pattern in SECRET_PATTERNS:
        found += [(kind, match.group()) for match in pattern.finditer(text)]
    return found


def find_secret(text: str, values: tuple[str, ...]) -> str | None:
    """Return the kind of the first secret in the text, or None.

    A secret is a credential value of this run or a text that matches a known secret pattern.
    The answer never holds the secret itself. It is safe to put in a comment.
    """
    found = _secrets_in(text, values)
    return found[0][0] if found else None


def find_new_secret(before: str, after: str, values: tuple[str, ...]) -> str | None:
    """Return the kind of the first secret that the new text holds more often than the old text.

    A secret that was in the old text is not new. So an edit next to an old key does not fail.
    """
    new = Counter(_secrets_in(after, values)) - Counter(_secrets_in(before, values))
    return next(iter(new))[0] if new else None
