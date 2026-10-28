from typing import Any

from pydantic import BaseModel, ConfigDict


class ToolDefinition(BaseModel):
    """A tool that the model can call. The schema is a JSON Schema of the arguments."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    parameters: dict[str, Any]
