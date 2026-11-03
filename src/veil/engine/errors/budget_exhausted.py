class BudgetExhausted(Exception):
    """The ticket used its token cap. The Engine stops the work on that ticket and makes it a Failed Fix."""
