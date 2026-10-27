from pydantic import BaseModel, ConfigDict, Field


class ReadFileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    start_line: int = Field(default=1, ge=1)
