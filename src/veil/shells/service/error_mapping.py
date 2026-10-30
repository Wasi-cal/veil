from collections.abc import Callable

from temporalio.exceptions import ApplicationError

from veil.engine.errors.model_client_error import ModelClientError
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.errors.tracker_error import TrackerError
from veil.shells.service.constants.retry import (
    SERVER_ERROR_STATUS,
    TRACKER_RETRY_STATUSES,
)


def to_application_error(
    error: Exception, redact: Callable[[str], str]
) -> ApplicationError:
    """Turn an Engine error into a Temporal error. Say if Temporal may retry the activity.

    Only an infrastructure failure may retry. A Failed Fix is a normal result and never reaches this function.
    A git or GitHub failure may retry too. The adapter cannot tell a lost network from a refused call.
    The message goes through `redact`, because Temporal stores it in the workflow history.
    """
    return ApplicationError(
        redact(str(error)),
        type=type(error).__name__,
        non_retryable=not _may_retry(error),
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
