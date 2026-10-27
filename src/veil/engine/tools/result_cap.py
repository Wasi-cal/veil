NARROW_NOTE = "The result is incomplete. Make the request narrower. For example, use a later start line or a more exact pattern."


def cap_result(text: str, limit: int) -> str:
    """Cut a tool result to `limit` bytes. Add the note that tells the model to narrow the request."""
    if len(text.encode()) <= limit:
        return text
    room = limit - len(NARROW_NOTE.encode()) - 1
    return f"{text.encode()[:room].decode(errors='ignore')}\n{NARROW_NOTE}"
