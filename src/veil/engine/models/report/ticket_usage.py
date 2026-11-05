from pydantic import BaseModel, Field


class ModelTokens(BaseModel):
    """The tokens that one model used for one ticket."""

    input: int = 0
    output: int = 0
    total: int = 0
    # The part of `input` that the API served from its cache. It costs less.
    cached: int = 0


class TicketUsage(BaseModel):
    """The tokens of one ticket, by model. `escalated` is true if the strong model ran."""

    by_model: dict[str, ModelTokens] = Field(default_factory=dict)
    escalated: bool = False

    @property
    def input(self) -> int:
        return sum(tokens.input for tokens in self.by_model.values())

    @property
    def output(self) -> int:
        return sum(tokens.output for tokens in self.by_model.values())

    @property
    def total(self) -> int:
        return sum(tokens.total for tokens in self.by_model.values())
