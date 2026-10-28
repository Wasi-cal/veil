from typing import Protocol, runtime_checkable

from veil.engine.models.llm.model_reply import ModelReply
from veil.engine.models.llm.tool_definition import ToolDefinition


@runtime_checkable
class ModelClient(Protocol):
    def next(
        self, messages: list[dict], model: str, tools: list[ToolDefinition]
    ) -> ModelReply:
        """Send the conversation and the tools to the model. Return its reply.

        Each message is in the chat format: a role, and content or tool calls.
        An assistant message holds the calls of the model, each with an id.
        A tool message holds a result and the id of the call that it answers.
        The reply must give the id of each call and the tokens that the API counted.
        """
        ...
