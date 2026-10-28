class AttemptFailed(Exception):
    """One attempt failed after the model started. A stronger model can try again.

    This is not a Failed Fix. Only a second failure becomes a Failed Fix.
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason
