from veil.engine import ModelReply, ToolCall


def edit_file(path: str, old: str, new: str) -> ToolCall:
    return ToolCall(name="edit_file", arguments={"path": path, "old": old, "new": new})


def read_file(path: str, **arguments) -> ToolCall:
    return ToolCall(name="read_file", arguments={"path": path, **arguments})


def search(pattern: str, **arguments) -> ToolCall:
    return ToolCall(name="search", arguments={"pattern": pattern, **arguments})


def list_dir(path: str = ".") -> ToolCall:
    return ToolCall(name="list_dir", arguments={"path": path})


def finish(summary: str) -> ToolCall:
    return ToolCall(name="finish", arguments={"summary": summary})


class FakeModelClient:
    """Play a script. Each model call returns one list of tool calls."""

    def __init__(self, script: list[list[ToolCall]], tokens_per_call: int = 0):
        self._script = list(script)
        self._tokens_per_call = tokens_per_call
        self.received: list[list[dict]] = []

    def everything_received(self) -> str:
        return "\n".join(m["content"] for call in self.received for m in call)

    def first_prompt(self) -> str:
        return self.received[0][0]["content"]

    def next(self, messages: list[dict]) -> ModelReply:
        self.received.append([dict(m) for m in messages])
        return ModelReply(tool_calls=self._script.pop(0), tokens=self._tokens_per_call)
