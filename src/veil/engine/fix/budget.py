from veil.engine.errors.budget_exhausted import BudgetExhausted
from veil.engine.models.llm.model_reply import ModelReply
from veil.engine.models.report.ticket_usage import ModelTokens, TicketUsage


class TicketBudget:
    """The tokens that one ticket may use, over all its attempts.

    The Engine makes a new budget for each ticket. A ticket that uses its cap becomes a Failed Fix.
    The run goes on with the next ticket. The budget also keeps the tokens of the ticket by model.
    """

    def __init__(self, cap: int) -> None:
        self.cap = cap
        self.used = 0
        self.usage = TicketUsage()

    def spend(self, model: str, reply: ModelReply) -> None:
        self.used += reply.tokens
        tokens = self.usage.by_model.setdefault(model, ModelTokens())
        tokens.total += reply.tokens
        tokens.input += reply.input_tokens
        tokens.output += reply.output_tokens
        tokens.cached += reply.cached_tokens

    def ensure(self) -> None:
        """Raise BudgetExhausted if the ticket used its cap. The Engine checks before each model call."""
        if self.used >= self.cap:
            raise BudgetExhausted
