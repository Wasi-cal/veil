from pydantic import BaseModel, ConfigDict, Field

from veil.adapters.openai.models.api_function_call import ApiFunctionCall


class ApiResponse(BaseModel):
    """What the client needs from a reply of the API: the function calls and the tokens that the API counted."""

    model_config = ConfigDict(frozen=True)

    function_calls: tuple[ApiFunctionCall, ...]
    total_tokens: int = Field(ge=0)
