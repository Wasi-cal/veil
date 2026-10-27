from pydantic import BaseModel, ConfigDict

from veil.engine.models.llm.tool_call import ToolCall


class ModelReply(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_calls: list[ToolCall]
    tokens: int = 0
