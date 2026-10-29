class TrackerError(Exception):
    """The tracker could not do its task. The adapter hides credential values in the message.

    `status` is the HTTP status of the failed call. It is None when the call got no usable answer.
    """

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status
