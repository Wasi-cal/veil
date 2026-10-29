class ModelClientError(Exception):
    """The model client could not get a reply. The adapter hides credential values in the message.

    A caller can read `retryable`. It is True when the same call can work later, for example after a rate limit.
    """

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable
