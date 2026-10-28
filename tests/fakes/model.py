import json

from veil.engine import ModelReply, ToolCall, ToolDefinition


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
        self.tools_received: list[list[ToolDefinition]] = []
        self.models_used: list[str] = []
        self._call_count = 0

    def everything_received(self) -> str:
        return "\n".join(
            m["content"] or json.dumps(m["tool_calls"])
            for call in self.received
            for m in call
        )

    def sent_by_the_engine(self) -> str:
        """Every message that the Engine wrote for the model. The tool calls of the model are not in it."""
        return "\n".join(
            m["content"] or ""
            for call in self.received
            for m in call
            if m["role"] != "assistant"
        )

    def first_prompt(self) -> str:
        return next(m["content"] for m in self.received[0] if m["role"] == "user")

    def next(
        self, messages: list[dict], model: str, tools: list[ToolDefinition]
    ) -> ModelReply:
        """Check the conversation as a real API does. Then return the next scripted reply."""
        _check_conversation(messages)
        self.models_used.append(model)
        self.received.append([dict(m) for m in messages])
        self.tools_received.append(list(tools))
        queue = self._shared if self._by_model is None else self._by_model[model]
        calls = []
        for call in queue.pop(0):
            self._call_count += 1
            calls.append(call.model_copy(update={"id": f"call_{self._call_count}"}))
        return ModelReply(tool_calls=calls, tokens=self._tokens_per_call)


def _check_conversation(messages: list[dict]) -> None:
    """Refuse a conversation that a real API refuses: a tool message without a call that it answers."""
    asked: set[str] = set()
    for message in messages:
        if message["role"] == "assistant":
            asked.update(call["id"] for call in message.get("tool_calls", []))
        if message["role"] == "tool" and message.get("tool_call_id") not in asked:
            raise ValueError("A tool message must answer a call of the model.")
