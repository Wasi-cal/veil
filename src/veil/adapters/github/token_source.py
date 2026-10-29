from typing import Protocol

from pydantic import SecretStr


class TokenSource(Protocol):
    """Where a Shell gets the GitHub token of one repository."""

    def mint(self, repo: str) -> SecretStr:
        """Return a short-lived token that covers this repository alone. Raise RepoProviderError on failure."""
        ...
