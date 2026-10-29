from veil.adapters.openai.models.api_function_call import ApiFunctionCall
from veil.adapters.openai.models.api_response import ApiResponse


def api_reply(*calls: tuple[str, str, str], tokens: int = 10) -> ApiResponse:
    """A reply of the API. Each call is (call id, tool name, arguments as the JSON text that the model wrote)."""
    return ApiResponse(
        function_calls=tuple(
            ApiFunctionCall(call_id=call_id, name=name, arguments=arguments)
            for call_id, name, arguments in calls
        ),
        total_tokens=tokens,
    )


class StubOpenAIApi:
    """An OpenAI API that plays a list of replies. A reply that is an exception is raised."""

    def __init__(self, replies: list[ApiResponse | Exception]):
        self._replies = list(replies)
        self.requests: list[dict] = []

    def create_response(
        self, model: str, input_items: list[dict], tools: list[dict]
    ) -> ApiResponse:
        self.requests.append({"model": model, "input": input_items, "tools": tools})
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply
