from veil.engine.errors.budget_exhausted import BudgetExhausted


class TicketBudget:
    """The tokens that one ticket may use, over all its attempts.

    The Engine makes a new budget for each ticket. A ticket that uses its cap becomes a Failed Fix.
    The run goes on with the next ticket.
    """

    def __init__(self, cap: int) -> None:
        self.cap = cap
        self.used = 0

    def spend(self, tokens: int) -> None:
        self.used += tokens

    def ensure(self) -> None:
        """Raise BudgetExhausted if the ticket used its cap. The Engine checks before each model call."""
        if self.used >= self.cap:
            raise BudgetExhausted
