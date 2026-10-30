from collections.abc import Callable

from veil.engine.errors.model_client_error import ModelClientError
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.errors.tracker_error import TrackerError
from veil.shells.service.constants.retry import (
    SERVER_ERROR_STATUS,
    TRACKER_RETRY_STATUSES,
)
from veil.shells.service.errors.run_failed import RunFailed


def classify_failure(error: Exception, redact: Callable[[str], str]) -> RunFailed:
    """Turn an Engine error into a run failure. Say if the run may retry.

    Only an infrastructure failure may retry. A Failed Fix is a normal result and never reaches this function.
    A git or GitHub failure may retry too. The adapter cannot tell a lost network from a refused call.
    The message goes through `redact`, because a runner may store it.
    """
    return RunFailed(
        redact(str(error)),
        error_type=type(error).__name__,
        retryable=_may_retry(error),
    )


def _may_retry(error: Exception) -> bool:
    if isinstance(error, ModelClientError):
        return error.retryable
    if isinstance(error, TrackerError):
        status = error.status
        return (
            status is None
            or status in TRACKER_RETRY_STATUSES
            or status >= SERVER_ERROR_STATUS
        )
    return isinstance(error, RepoProviderError)
