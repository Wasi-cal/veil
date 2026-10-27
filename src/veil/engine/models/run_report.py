from pydantic import BaseModel, Field


class RunReport(BaseModel):
    pull_requests: list[str] = Field(default_factory=list)
    outcomes: dict[str, str] = Field(default_factory=dict)
    tokens_used: int = 0
