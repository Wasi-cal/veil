class BudgetExhausted(Exception):
    """The run used its token ceiling. The Engine stops. It does not touch the rest of the tickets."""
