class RepoProviderError(Exception):
    """The repo provider could not do its task. The adapter hides credential values in the message."""
