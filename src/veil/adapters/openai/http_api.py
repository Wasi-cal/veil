from pydantic import SecretStr

from veil.adapters.json_http import call_json, require_https
from veil.adapters.openai.constants.http import (
    API_URL,
    MODEL_CALL_TIMEOUT_SECONDS,
    PERMANENT_ERROR_CODES,
    RESPONSES_PATH,
    RETRYABLE_ERROR_CODES,
    RETRYABLE_STATUSES,
    SERVER_ERROR_STATUS,
)
from veil.adapters.openai.constants.items import OUTPUT_FUNCTION_CALL, STATUS_FAILED
from veil.adapters.openai.constants.messages import NO_USAGE
from veil.adapters.openai.models.api_function_call import ApiFunctionCall
from veil.adapters.openai.models.api_response import ApiResponse
from veil.engine.errors.model_client_error import ModelClientError
from veil.engine.secrets.redact import redact


class HttpOpenAIApi:
    """The OpenAI Responses API over HTTP. The key goes in the Authorization header and nowhere else.

    Each call is stateless. It stores nothing at OpenAI and sends the whole conversation.
    """

    def __init__(
        self,
        api_key: SecretStr,
        base_url: str = API_URL,
        timeout_seconds: float = MODEL_CALL_TIMEOUT_SECONDS,
    ):
        require_https(base_url, ModelClientError, "OpenAI")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def create_response(
        self, model: str, input_items: list[dict], tools: list[dict]
    ) -> ApiResponse:
        key = self._api_key.get_secret_value()
        reply = call_json(
            service="OpenAI",
            error=_failed_call,
            secrets=(key,),
            base_url=self._base_url,
            method="POST",
            path=RESPONSES_PATH,
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            body={"model": model, "input": input_items, "tools": tools, "store": False},
            timeout=self._timeout,
        )
        try:
            return _parse(reply, key)
        except (KeyError, TypeError, AttributeError, ValueError):
            raise ModelClientError(
                "OpenAI gave a reply in an unexpected shape."
            ) from None


def _parse(reply: object, key: str) -> ApiResponse:
    if not isinstance(reply, dict):
        raise TypeError("The reply is not an object.")
    if reply.get("status") == STATUS_FAILED:
        failure = reply.get("error") or {}
        code = str(failure.get("code", "unknown"))
        message = redact(
            f"OpenAI failed the response. Code {code}. {failure.get('message', '')}",
            (key,),
        )
        raise ModelClientError(message, retryable=code in RETRYABLE_ERROR_CODES)
    output = reply["output"]
    if not isinstance(output, list):
        raise TypeError("The output is not a list.")
    calls = []
    for item in output:
        if item["type"] != OUTPUT_FUNCTION_CALL:
            continue
        if not isinstance(item["arguments"], str):
            raise TypeError("The arguments are not text.")
        calls.append(
            ApiFunctionCall(
                call_id=item["call_id"], name=item["name"], arguments=item["arguments"]
            )
        )
    return ApiResponse(function_calls=tuple(calls), total_tokens=_tokens(reply))


def _tokens(reply: dict) -> int:
    """The tokens that the API counted. Raise if the reply has no usage. Never count zero."""
    usage = reply.get("usage")
    if not isinstance(usage, dict):
        raise ModelClientError(NO_USAGE)
    counts = {name: value for name, value in usage.items() if isinstance(value, int)}
    if "total_tokens" in counts:
        return counts["total_tokens"]
    parts = [
        counts[name] for name in ("input_tokens", "output_tokens") if name in counts
    ]
    if not parts:
        raise ModelClientError(NO_USAGE)
    return sum(parts)


def _failed_call(message: str, status: int | None) -> ModelClientError:
    """A failed call. A retry can help after a rate limit or a server error, but not when the quota is gone.

    A call that got no answer also counts as one that a retry can help.
    """
    if any(code in message for code in PERMANENT_ERROR_CODES):
        return ModelClientError(message, retryable=False)
    retryable = (
        status is None or status in RETRYABLE_STATUSES or status >= SERVER_ERROR_STATUS
    )
    return ModelClientError(message, retryable=retryable)
