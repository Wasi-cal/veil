import base64
from typing import Any, TypeVar, overload
from urllib.parse import urlsplit

from veil.adapters.jira.constants.http import (
    LOCAL_HOSTS,
)
from veil.adapters.jira.models.jira_credentials import JiraCredentials
from veil.adapters.json_http import call_json
from veil.engine.errors.tracker_error import TrackerError

T = TypeVar("T")


class JiraHttp:
    """Calls the Jira REST API with JSON. The credentials go in the Authorization header and nowhere else."""

    def __init__(self, api_base: str, credentials: JiraCredentials | None):
        parts = urlsplit(api_base)
        if parts.scheme != "https" and not (
            parts.scheme == "http" and parts.hostname in LOCAL_HOSTS
        ):
            raise TrackerError("Refused the Jira URL. It must use https.")
        self._api_base = api_base.rstrip("/")
        self._authorization: str | None = None
        self._secrets: tuple[str, ...] = ()
        if credentials is None:
            return
        token = credentials.api_token.get_secret_value()
        if credentials.email:
            basic = base64.b64encode(f"{credentials.email}:{token}".encode()).decode()
            self._authorization = f"Basic {basic}"
            self._secrets = (token, basic)
        else:
            self._authorization = f"Bearer {token}"
            self._secrets = (token,)

    @overload
    def call(
        self,
        method: str,
        path: str,
        params: dict[str, str | int] | None = None,
        body: dict | None = None,
        *,
        shape: type[T],
    ) -> T: ...

    @overload
    def call(
        self,
        method: str,
        path: str,
        params: dict[str, str | int] | None = None,
        body: dict | None = None,
        shape: None = None,
    ) -> Any: ...

    def call(
        self,
        method: str,
        path: str,
        params: dict[str, str | int] | None = None,
        body: dict | None = None,
        shape: type | None = None,
    ) -> Any:
        reply = call_json(
            service="Jira",
            error=TrackerError,
            secrets=self._secrets,
            base_url=self._api_base,
            method=method,
            path=path,
            params=params,
            body=body,
            headers={
                "Accept": "application/json",
                **(
                    {"Authorization": self._authorization}
                    if self._authorization
                    else {}
                ),
            },
        )
        if shape is not None and not isinstance(reply, shape):
            raise TrackerError(f"Jira {method} {path} gave a reply of the wrong kind.")
        return reply
