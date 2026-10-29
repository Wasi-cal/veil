import time
from typing import Any

import jwt
from pydantic import SecretStr

from veil.adapters.github.constants.app import (
    IMPLIED_PERMISSIONS,
    JWT_ALGORITHM,
    JWT_BACKDATE_SECONDS,
    JWT_LIFETIME_SECONDS,
    KEY_NOT_VALID,
    NOT_INSTALLED,
    REASON_NO_TOKEN,
    REASON_PERMISSIONS,
    REASON_REPOS,
    TOKEN_CHECK_FAILED,
    TOKEN_PERMISSIONS,
)
from veil.adapters.github.constants.http import API_URL, API_VERSION
from veil.adapters.github.constants.repo_name import REPO_NAME
from veil.adapters.json_http import call_json, require_https
from veil.engine.errors.repo_provider_error import RepoProviderError


class GitHubAppTokenSource:
    """Mint a short-lived GitHub App installation token for one repository.

    The token covers that repository alone. It holds the permissions contents and pull requests, both write.
    The source checks the reply before it gives the token out. It keeps no token and no JWT.
    """

    def __init__(
        self, app_id: str, private_key: SecretStr, base_url: str = API_URL
    ) -> None:
        require_https(base_url, RepoProviderError, "GitHub")
        self._app_id = app_id
        self._private_key = private_key
        self._base_url = base_url.rstrip("/")

    def mint(self, repo: str) -> SecretStr:
        """Return a token for `repo`. Raise RepoProviderError if any step or the check fails.

        The error never repeats the key, the JWT or the token.
        """
        if not REPO_NAME.fullmatch(repo) or ".." in repo:
            raise RepoProviderError("Refused the repository name.")
        app_jwt = self._sign()
        installation = self._call(
            app_jwt,
            "GET",
            f"/repos/{repo}/installation",
            not_found=NOT_INSTALLED.format(repo=repo),
        )
        name = repo.split("/")[1]
        reply = self._call(
            app_jwt,
            "POST",
            f"/app/installations/{int(installation['id'])}/access_tokens",
            body={"repositories": [name], "permissions": dict(TOKEN_PERMISSIONS)},
        )
        return self._checked(reply, repo)

    def _sign(self) -> str:
        now = int(time.time())
        claims = {
            "iss": self._app_id,
            "iat": now - JWT_BACKDATE_SECONDS,
            "exp": now + JWT_LIFETIME_SECONDS,
        }
        try:
            return jwt.encode(
                claims,
                self._private_key.get_secret_value(),
                algorithm=JWT_ALGORITHM,
            )
        except Exception:  # noqa: BLE001 - any signing error may quote the key, so drop it
            raise RepoProviderError(KEY_NOT_VALID) from None

    def _call(
        self,
        app_jwt: str,
        method: str,
        path: str,
        body: dict | None = None,
        not_found: str | None = None,
    ) -> Any:
        def error(message: str, status: int | None) -> Exception:
            if status == 404 and not_found:
                return RepoProviderError(not_found)
            return RepoProviderError(message)

        reply = call_json(
            service="GitHub",
            error=error,
            secrets=(app_jwt, self._private_key.get_secret_value()),
            base_url=self._base_url,
            method=method,
            path=path,
            body=body,
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
            },
        )
        if not isinstance(reply, dict):
            raise RepoProviderError(f"GitHub {method} {path} gave no usable reply.")
        return reply

    @staticmethod
    def _checked(reply: dict, repo: str) -> SecretStr:
        token = reply.get("token")
        if not isinstance(token, str) or not token:
            raise RepoProviderError(TOKEN_CHECK_FAILED.format(reason=REASON_NO_TOKEN))
        covered = [item.get("full_name") for item in reply.get("repositories") or []]
        if reply.get("repository_selection") != "selected" or covered != [repo]:
            raise RepoProviderError(TOKEN_CHECK_FAILED.format(reason=REASON_REPOS))
        granted = dict(reply.get("permissions") or {})
        for name, level in IMPLIED_PERMISSIONS.items():
            if granted.get(name) == level:
                del granted[name]
        if granted != TOKEN_PERMISSIONS:
            raise RepoProviderError(
                TOKEN_CHECK_FAILED.format(reason=REASON_PERMISSIONS)
            )
        return SecretStr(token)
