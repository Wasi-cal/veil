import pytest

from veil.engine.errors.model_client_error import ModelClientError
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.errors.settings_error import SettingsError
from veil.engine.errors.token_expired import TokenExpired
from veil.engine.errors.tracker_error import TrackerError
from veil.shells.service.classify_failure import classify_failure
from veil.shells.service.errors.run_failed import RunFailed


def classified(error, redact=lambda text: text):
    result = classify_failure(error, redact)
    assert isinstance(result, RunFailed)
    return result


@pytest.mark.parametrize(
    "error",
    [
        ModelClientError("rate limit", retryable=True),
        TrackerError("down", status=503),
        TrackerError("slow", status=429),
        TrackerError("timeout", status=408),
        TrackerError("no answer", status=None),
        RepoProviderError("git failed"),
    ],
)
def test_an_infrastructure_failure_may_be_retried(error):
    assert classified(error).retryable is True


@pytest.mark.parametrize(
    "error",
    [
        ModelClientError("no quota", retryable=False),
        TrackerError("bad login", status=401),
        TrackerError("not found", status=404),
        SettingsError(["bad value"]),
        TokenExpired("the token expired"),
        ValueError("a bug"),
    ],
)
def test_any_other_failure_is_not_retried(error):
    assert classified(error).retryable is False


def test_the_message_goes_through_redact_and_the_type_names_the_error():
    result = classified(
        TrackerError("token abc12345 failed", status=500),
        lambda t: t.replace("abc12345", "[redacted]"),
    )

    assert "abc12345" not in str(result)
    assert "[redacted]" in str(result)
    assert result.error_type == "TrackerError"
