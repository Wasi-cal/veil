from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)


class FinishArgs(BaseModel):
    """What the model gives when it calls finish: a one-line commit message and three short parts.

    `problem` says why this code is a problem. `change` says what the model changed.
    `solves` says what the change solves. The three parts go into the PR and the ticket comment.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    commit_message: str
    problem: str
    change: str
    solves: str
    breaking: bool
    breaking_reason: str | None = None

    @field_validator("commit_message")
    @classmethod
    def _one_line(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("The commit message is empty.")
        if "\n" in value:
            raise ValueError("The commit message must be one line.")
        return value

    @field_validator("problem", "change", "solves")
    @classmethod
    def _not_empty(cls, value: str, info: ValidationInfo) -> str:
        value = value.strip()
        if not value:
            raise ValueError(f"The part {info.field_name} is empty.")
        return value

    @model_validator(mode="after")
    def _reason_when_breaking(self) -> "FinishArgs":
        reason = (self.breaking_reason or "").strip()
        if self.breaking and not reason:
            raise ValueError(
                "The part breaking_reason is empty. Give a reason when breaking is true."
            )
        object.__setattr__(self, "breaking_reason", reason if self.breaking else None)
        return self
