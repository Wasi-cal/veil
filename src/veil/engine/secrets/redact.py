from veil.engine.constants.secrets import REDACTED, SECRET_PATTERNS


def redact(text: str, values: tuple[str, ...]) -> str:
    """Replace each credential value and each text that matches a secret pattern with [redacted].

    Two matches that overlap become one [redacted]. So no part of a secret stays in the text.
    """
    spans = _spans(text, values)
    out: list[str] = []
    position = 0
    for start, end in _merged(spans):
        out.append(text[position:start])
        out.append(REDACTED)
        position = end
    out.append(text[position:])
    return "".join(out)


def _spans(text: str, values: tuple[str, ...]) -> list[tuple[int, int]]:
    spans = []
    for value in filter(None, values):
        start = text.find(value)
        while start != -1:
            spans.append((start, start + len(value)))
            start = text.find(value, start + 1)
    for _, pattern in SECRET_PATTERNS:
        spans.extend(match.span() for match in pattern.finditer(text))
    return spans


def _merged(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
