from typing import Protocol

from veil.adapters.openai.models.api_response import ApiResponse


class OpenAIApi(Protocol):
    """The part of the OpenAI Responses API that the model client needs."""

    def create_response(
        self, model: str, input_items: list[dict], tools: list[dict]
    ) -> ApiResponse:
        """Send the input items and the tools. Return the function calls and the tokens that the API counted.

        Raise ModelClientError if the API gives no usable reply.
        """
        ...
