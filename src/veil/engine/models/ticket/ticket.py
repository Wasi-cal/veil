from pydantic import BaseModel, ConfigDict


class Ticket(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    repo: str
    file: str
    line: int
    severity: str
    finding: str
