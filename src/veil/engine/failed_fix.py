class FailedFix(Exception):
    """The Engine could not fix a Gozu Ticket within its limits. `reason` goes in the comment."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason
