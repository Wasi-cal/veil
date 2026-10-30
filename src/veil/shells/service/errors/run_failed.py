class RunFailed(Exception):
    """A run of the Engine for one repo stopped with an error. The message holds no credential.

    `retryable` says if the same run may work later. A lost network can. A refused login cannot.
    """

    def __init__(self, message: str, error_type: str, retryable: bool) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable
