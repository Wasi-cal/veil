from veil.engine.constants.secret_patterns import SECRET_PATTERNS

REDACTED = "[redacted]"


def redact(text: str, values: tuple[str, ...]) -> str:
    """Replace each credential value and each text that matches a secret pattern with [redacted].

    The longest credential value goes first.
    """
    for value in sorted(filter(None, values), key=len, reverse=True):
        text = text.replace(value, REDACTED)
    for _, pattern in SECRET_PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text
