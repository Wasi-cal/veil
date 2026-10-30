import time
from typing import Any

import jwt
from pydantic import SecretStr

from veil.adapters.github.constants.app import (
    ACCOUNT_NAME,
    ACCOUNT_REFUSED,
    APP_CHECK_FAILED,
    APP_PERMISSIONS,
    APP_SLUG,
    BOT_SUFFIX,
    IMPLIED_PERMISSIONS,
    JWT_ALGORITHM,
    JWT_BACKDATE_SECONDS,
    JWT_LIFETIME_SECONDS,
    KEY_NOT_VALID,
    LIST_PAGE_LIMIT,
    LIST_REFUSED,
    NOT_INSTALLED,
    REASON_APP_EVENTS,
    REASON_APP_PERMISSIONS,
    REASON_APP_REPLY,
    REASON_LIST_PERMISSIONS,
    REASON_LIST_TOO_LONG,
    REASON_NO_TOKEN,
    REASON_PERMISSIONS,
    REASON_REPOS,
    TOKEN_CHECK_FAILED,
    TOKEN_PERMISSIONS,
)
from veil.adapters.github.constants.http import API_URL, API_VERSION, PAGE_SIZE
from veil.adapters.github.constants.repo_name import REPO_NAME
from veil.adapters.github.models.github_app import GitHubApp
from veil.adapters.json_http import call_json, require_https
from veil.engine.errors.repo_provider_error import RepoProviderError


class _NotInstalled(RepoProviderError):
    """GitHub answered 404 to a lookup of an installation."""


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

    def installation_id(self, owner: str) -> int:
        """Return the ID of the installation of the App on an organization or a user. Needs the JWT only."""
        if not ACCOUNT_NAME.fullmatch(owner):
            raise RepoProviderError(ACCOUNT_REFUSED)
        app_jwt = self._sign()
        not_installed = NOT_INSTALLED.format(repo=owner)
        try:
            found = self._call(
                app_jwt, "GET", f"/orgs/{owner}/installation", not_found=not_installed
            )
        except _NotInstalled:
            found = self._call(
                app_jwt, "GET", f"/users/{owner}/installation", not_found=not_installed
            )
        return int(found["id"])

    def list_repos(self, installation_id: int) -> list[str]:
        """Return the full names of the repos of an installation, in the order of GitHub.

        The call mints a token that reads metadata only. It uses the token for the list and drops it.
        """
        app_jwt = self._sign()
        reply = self._call(
            app_jwt,
            "POST",
            f"/app/installations/{int(installation_id)}/access_tokens",
            body={"permissions": dict(IMPLIED_PERMISSIONS)},
        )
        token = reply.get("token")
        if not isinstance(token, str) or not token:
            raise RepoProviderError(LIST_REFUSED.format(reason=REASON_NO_TOKEN))
        if dict(reply.get("permissions") or {}) != IMPLIED_PERMISSIONS:
            raise RepoProviderError(LIST_REFUSED.format(reason=REASON_LIST_PERMISSIONS))
        repos: list[str] = []
        for page in range(1, LIST_PAGE_LIMIT + 1):
            names = self._list_page(token, page)
            repos.extend(names)
            if len(names) < PAGE_SIZE:
                return repos
        raise RepoProviderError(LIST_REFUSED.format(reason=REASON_LIST_TOO_LONG))

    def _list_page(self, token: str, page: int) -> list[str]:
        reply = self._call(
            token,
            "GET",
            "/installation/repositories",
            params={"per_page": PAGE_SIZE, "page": page},
        )
        names = [item.get("full_name") for item in reply.get("repositories") or []]
        if not all(isinstance(n, str) and REPO_NAME.fullmatch(n) for n in names):
            raise RepoProviderError(LIST_REFUSED.format(reason=REASON_APP_REPLY))
        return names

    def read_app(self) -> GitHubApp:
        """Read the App and check it. A worker calls it at start. It needs the JWT only.

        The App must hold the three permissions and no others. It must listen to no events.
        Raise RepoProviderError if it does not.
        GitHub does not report if the webhook is on. The check of the events is the nearest check that the API allows.
        """
        app_jwt = self._sign()
        app = self._call(app_jwt, "GET", "/app")
        slug = app.get("slug")
        if not isinstance(slug, str) or not APP_SLUG.fullmatch(slug):
            raise RepoProviderError(APP_CHECK_FAILED.format(reason=REASON_APP_REPLY))
        if dict(app.get("permissions") or {}) != APP_PERMISSIONS:
            raise RepoProviderError(
                APP_CHECK_FAILED.format(reason=REASON_APP_PERMISSIONS)
            )
        if app.get("events"):
            raise RepoProviderError(APP_CHECK_FAILED.format(reason=REASON_APP_EVENTS))
        bot = self._call(app_jwt, "GET", f"/users/{slug}{BOT_SUFFIX}")
        user_id = bot.get("id")
        if not isinstance(user_id, int):
            raise RepoProviderError(APP_CHECK_FAILED.format(reason=REASON_APP_REPLY))
        return GitHubApp(slug=slug, bot_user_id=user_id)

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
        bearer: str,
        method: str,
        path: str,
        body: dict | None = None,
        not_found: str | None = None,
        params: dict[str, str | int] | None = None,
    ) -> Any:
        def error(message: str, status: int | None) -> Exception:
            if status == 404 and not_found:
                return _NotInstalled(not_found)
            return RepoProviderError(message)

        reply = call_json(
            service="GitHub",
            error=error,
            secrets=(bearer, self._private_key.get_secret_value()),
            base_url=self._base_url,
            method=method,
            path=path,
            params=params,
            body=body,
            headers={
                "Authorization": f"Bearer {bearer}",
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
