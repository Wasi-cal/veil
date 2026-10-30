from veil.engine.errors.repo_provider_error import RepoProviderError


class TokenExpired(RepoProviderError):
    """GitHub refused the token of the run. The token expired or somebody revoked it.

    The Engine stops the repo. Another token needs a new run.
    """
