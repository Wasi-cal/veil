from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    """Defaults live in code. Callers pass their own values in."""

    model_config = ConfigDict(frozen=True)
