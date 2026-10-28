import http.client
import json
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode

from veil.adapters.constants.http import ERROR_DETAIL_MAX_CHARS, TIMEOUT_SECONDS
from veil.adapters.no_redirect import open_without_redirect
from veil.engine.secrets.redact import redact


def call_json(
    *,
    service: str,
    error: type[Exception],
    secrets: tuple[str, ...],
    base_url: str,
    method: str,
    path: str,
    headers: dict[str, str],
    params: dict[str, str | int] | None = None,
    body: dict | None = None,
):
    """Call a JSON API and return the decoded reply. An empty reply gives None.

    Any failure raises `error` with the credential values hidden. A redirect is a failure.
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
        with open_without_redirect(request, TIMEOUT_SECONDS) as response:
            raw = response.read()
    except urllib.error.HTTPError as failure:
        detail = failure.read().decode(errors="replace")[:ERROR_DETAIL_MAX_CHARS]
        raise error(
            redact(
                f"{service} {method} {path} failed with {failure.code}. {detail}",
                secrets,
            )
        ) from None
    except (urllib.error.URLError, http.client.HTTPException, OSError) as failure:
        raise error(
            redact(f"{service} {method} {path} failed. {failure}", secrets)
        ) from None
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        raise error(
            f"{service} {method} {path} gave a reply that is not JSON."
        ) from None
