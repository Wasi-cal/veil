from veil.engine import ModelReply, ToolCall


def edit_file(path: str, old: str, new: str) -> ToolCall:
    return ToolCall(name="edit_file", arguments={"path": path, "old": old, "new": new})


def finish(summary: str) -> ToolCall:
    return ToolCall(name="finish", arguments={"summary": summary})


class FakeModelClient:
    """Plays back a script: one list of tool calls per model call."""

    def __init__(self, script: list[list[ToolCall]], tokens_per_call: int = 0):
        self._script = list(script)
        self._tokens_per_call = tokens_per_call
        self.received: list[list[dict]] = []

    def first_prompt(self) -> str:
        return self.received[0][0]["content"]

    def next(self, messages: list[dict]) -> ModelReply:
        self.received.append([dict(m) for m in messages])
        return ModelReply(tool_calls=self._script.pop(0), tokens=self._tokens_per_call)
