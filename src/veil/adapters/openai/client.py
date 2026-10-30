import json
import time
from collections.abc import Callable

from veil.adapters.openai.api import OpenAIApi
from veil.adapters.openai.constants.items import (
    FUNCTION_CALL,
    FUNCTION_CALL_OUTPUT,
    FUNCTION_TOOL,
    ROLE_ASSISTANT,
    ROLE_TOOL,
)
from veil.adapters.openai.constants.retry import (
    MODEL_CALL_RETRIES,
    RETRY_BASE_DELAY_SECONDS,
    RETRY_MAX_DELAY_SECONDS,
)
from veil.adapters.openai.models.api_response import ApiResponse
from veil.engine.errors.model_client_error import ModelClientError
from veil.engine.models.llm.model_reply import ModelReply
from veil.engine.models.llm.tool_call import ToolCall
from veil.engine.models.llm.tool_definition import ToolDefinition


class OpenAIModelClient:
    """The real model client. It satisfies the ModelClient interface of the Engine.

    It turns the chat messages of the Engine into items of the Responses API, and the reply into a ModelReply.
    It keeps no state. The Engine sends the whole conversation on each call.
    A failed call with `retryable` set is tried again at most twice, with a growing pause.
    A rejected call costs no tokens, so a new try keeps the token ceiling intact.
    """

    def __init__(
        self, api: OpenAIApi, sleep: Callable[[float], None] = time.sleep
    ) -> None:
        self._api = api
        self._sleep = sleep

    def next(
        self, messages: list[dict], model: str, tools: list[ToolDefinition]
    ) -> ModelReply:
        response = self._create(model, _items(messages), [_tool(t) for t in tools])
        return ModelReply(
            tool_calls=[
                ToolCall(
                    id=call.call_id,
                    name=call.name,
                    arguments=_arguments(call.arguments),
                )
                for call in response.function_calls
            ],
            tokens=response.total_tokens,
        )

    def _create(self, model: str, items: list[dict], tools: list[dict]) -> ApiResponse:
        for attempt in range(MODEL_CALL_RETRIES):
            try:
                return self._api.create_response(model, items, tools)
            except ModelClientError as failure:
                if not failure.retryable:
                    raise
                self._sleep(
                    min(RETRY_MAX_DELAY_SECONDS, RETRY_BASE_DELAY_SECONDS * 2**attempt)
                )
        return self._api.create_response(model, items, tools)


def _tool(tool: ToolDefinition) -> dict:
    return {
        "type": FUNCTION_TOOL,
        # The Engine checks the arguments itself. Strict mode would make the API change the schema.
        "strict": False,
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters,
    }


def _items(messages: list[dict]) -> list[dict]:
    """Chat messages to items. A call goes without the id of the API, so the API asks for no reasoning item."""
    items: list[dict] = []
    asked: set[str] = set()
    for message in messages:
        role = message["role"]
        if role == ROLE_ASSISTANT:
            if message.get("content"):
                items.append({"role": role, "content": message["content"]})
            for call in message.get("tool_calls") or []:
                asked.add(call["id"])
                items.append(
                    {
                        "type": FUNCTION_CALL,
                        "call_id": call["id"],
                        "name": call["function"]["name"],
                        "arguments": call["function"]["arguments"],
                    }
                )
        elif role == ROLE_TOOL:
            if message["tool_call_id"] not in asked:
                raise ModelClientError("A tool message answers no call of the model.")
            items.append(
                {
                    "type": FUNCTION_CALL_OUTPUT,
                    "call_id": message["tool_call_id"],
                    "output": message["content"],
                }
            )
        else:
            items.append({"role": role, "content": message["content"]})
    return items


def _arguments(written: str) -> dict:
    """The arguments that the model wrote. Text that is not a JSON object gives none.

    The Engine then answers the bad call with an error text, and the model can try again.
    """
    try:
        value = json.loads(written)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
