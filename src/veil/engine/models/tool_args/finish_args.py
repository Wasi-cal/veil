from pydantic import BaseModel, ConfigDict, field_validator


class FinishArgs(BaseModel):
    """What the model gives when it calls finish: a one-line commit message and a short explanation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    commit_message: str
    explanation: str

    @field_validator("commit_message")
    @classmethod
    def _one_line(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("The commit message is empty.")
        if "\n" in value:
            raise ValueError("The commit message must be one line.")
        return value

    @field_validator("explanation")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("The explanation is empty.")
        return value
