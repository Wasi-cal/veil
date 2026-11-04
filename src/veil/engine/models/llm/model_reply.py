from pydantic import BaseModel, ConfigDict, Field

from veil.engine.models.llm.tool_call import ToolCall


class ModelReply(BaseModel):
    """One reply from the model. The client must report the tokens that the API counted."""

    model_config = ConfigDict(frozen=True)

    tool_calls: list[ToolCall]
    tokens: int = Field(ge=0)
    # The split of `tokens`. A reply that counts only the total leaves both at 0.
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
