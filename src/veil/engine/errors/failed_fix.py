class FailedFix(Exception):
    """The Engine cannot fix a Gozu Ticket within its limits. The `reason` goes in the comment on the ticket."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason
