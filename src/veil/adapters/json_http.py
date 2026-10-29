import http.client
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from urllib.parse import quote, urlencode, urlsplit

from veil.adapters.constants.http import (
    ERROR_DETAIL_MAX_CHARS,
    LOCAL_HOSTS,
    TIMEOUT_SECONDS,
)
from veil.adapters.no_redirect import open_without_redirect
from veil.engine.secrets.redact import redact


def plain_error(error: type[Exception]) -> Callable[[str, int | None], Exception]:
    """An error factory for a caller that does not need the HTTP status."""
    return lambda message, _status: error(message)


def require_https(url: str, error: type[Exception], service: str) -> None:
    """Raise `error` unless the URL uses https. Only a local host may use http."""
    parts = urlsplit(url)
    if parts.scheme != "https" and not (
        parts.scheme == "http" and parts.hostname in LOCAL_HOSTS
    ):
        raise error(f"Refused the {service} URL. It must use https.")


def call_json(
    *,
    service: str,
    error: Callable[[str, int | None], Exception],
    secrets: tuple[str, ...],
    base_url: str,
    method: str,
    path: str,
    headers: dict[str, str],
    params: dict[str, str | int] | None = None,
    body: dict | None = None,
    timeout: float = TIMEOUT_SECONDS,
):
    """Call a JSON API and return the decoded reply. An empty reply gives None.

    Any failure raises `error` with the credential values hidden. A redirect is a failure.
    `error` makes the error for a failed call. It gets the message and the HTTP status.
    The status is None when the call never got an answer or the reply was not JSON.
    """

    url = base_url.rstrip("/") + quote(path, safe="/")
    if params:
        url += "?" + urlencode(params)
    request = urllib.request.Request(
        url,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with open_without_redirect(request, timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as failure:
        detail = failure.read().decode(errors="replace")[:ERROR_DETAIL_MAX_CHARS]
        message = redact(
            f"{service} {method} {path} failed with {failure.code}. {detail}",
            secrets,
        )
        raise error(message, failure.code) from None
    except (urllib.error.URLError, http.client.HTTPException, OSError) as failure:
        message = redact(f"{service} {method} {path} failed. {failure}", secrets)
        raise error(message, None) from None
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        raise error(
            f"{service} {method} {path} gave a reply that is not JSON.", None
        ) from None
