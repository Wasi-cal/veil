from veil.engine import ModelReply, ToolCall


def edit_file(path: str, old: str, new: str) -> ToolCall:
    return ToolCall(name="edit_file", arguments={"path": path, "old": old, "new": new})


def read_file(path: str, **arguments) -> ToolCall:
    return ToolCall(name="read_file", arguments={"path": path, **arguments})


def search(pattern: str, **arguments) -> ToolCall:
    return ToolCall(name="search", arguments={"pattern": pattern, **arguments})


def list_dir(path: str = ".") -> ToolCall:
    return ToolCall(name="list_dir", arguments={"path": path})


def finish(
    explanation: str = "Fixed.", commit_message: str = "Fix the finding."
) -> ToolCall:
    return ToolCall(
        name="finish",
        arguments={"commit_message": commit_message, "explanation": explanation},
    )


class FakeModelClient:
    """Play a script. Each model call returns one list of tool calls.

    Give a list to use one script for every model. Give a dictionary to use one script for each model name.
    """

    def __init__(
        self,
        script: list[list[ToolCall]] | dict[str, list[list[ToolCall]]],
        tokens_per_call: int = 0,
    ):
        self._by_model = (
            {name: list(calls) for name, calls in script.items()}
            if isinstance(script, dict)
            else None
        )
        self._shared = None if isinstance(script, dict) else list(script)
        self._tokens_per_call = tokens_per_call
        self.received: list[list[dict]] = []
        self.models_used: list[str] = []

    def everything_received(self) -> str:
        return "\n".join(m["content"] for call in self.received for m in call)

    def first_prompt(self) -> str:
        return self.received[0][0]["content"]

    def next(self, messages: list[dict], model: str) -> ModelReply:
        self.models_used.append(model)
        self.received.append([dict(m) for m in messages])
        queue = self._shared if self._by_model is None else self._by_model[model]
        return ModelReply(tool_calls=queue.pop(0), tokens=self._tokens_per_call)
