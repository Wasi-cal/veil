from pydantic import BaseModel, ConfigDict, Field


class ModelPrice(BaseModel):
    """What one model costs, in US dollars for 1 million tokens."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input: float = Field(ge=0)
    cached_input: float = Field(ge=0)
    output: float = Field(ge=0)
