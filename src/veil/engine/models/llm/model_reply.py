from pydantic import BaseModel, ConfigDict, Field

from veil.engine.models.llm.tool_call import ToolCall


class ModelReply(BaseModel):
    """One reply from the model. The client must report the tokens that the API counted."""

    model_config = ConfigDict(frozen=True)

    tool_calls: list[ToolCall]
    tokens: int = Field(ge=0)
