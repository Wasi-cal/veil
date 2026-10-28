import json
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode

from pydantic import SecretStr

from veil.adapters.github.constants.http import (
    API_URL,
    API_VERSION,
    ERROR_DETAIL_MAX_CHARS,
    PAGE_SIZE,
    TIMEOUT_SECONDS,
)
from veil.adapters.github.constants.pr_states import MERGED, PrState
from veil.adapters.github.constants.repo_name import REPO_NAME
from veil.adapters.github.models.pull_request import PullRequest
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.secrets.redact import redact


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect. A redirect could send the token to another host."""

    def redirect_request(self, *_args, **_kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


class HttpGitHubApi:
    """The GitHub REST API over HTTP. The token goes in the Authorization header and nowhere else.

    One call reads one page of at most 100 PRs.
    """

    def __init__(self, token: SecretStr, base_url: str = API_URL):
        self._token = token
        self._base_url = base_url.rstrip("/")

    def find_pull_requests(
        self, repo: str, head: str | None = None, label: str | None = None
    ) -> list[PullRequest]:
        self._check_repo(repo)
        if label is not None:
            query = f'repo:{repo} is:pr label:"{label}"'
            found = self._call(
                "GET", "/search/issues", {"q": query, "per_page": PAGE_SIZE}
            )
            raw = [
                self._call("GET", f"/repos/{repo}/pulls/{int(item['number'])}")
                for item in found["items"]
            ]
        else:
            params: dict[str, str | int] = {"state": "all", "per_page": PAGE_SIZE}
            if head is not None:
                params["head"] = f"{repo.split('/')[0]}:{head}"
            raw = self._call("GET", f"/repos/{repo}/pulls", params)
        found_prs = [self._pull_request(item) for item in raw]
        return [pr for pr in found_prs if head is None or pr.head_branch == head]

    def create_draft_pr(
        self,
        repo: str,
        head: str,
        base: str,
        title: str,
        body: str,
        labels: tuple[str, ...],
    ) -> PullRequest:
        self._check_repo(repo)
        created = self._call(
            "POST",
            f"/repos/{repo}/pulls",
            body={
                "title": title,
                "head": head,
                "base": base,
                "body": body,
                "draft": True,
            },
        )
        if labels:
            self._call(
                "POST",
                f"/repos/{repo}/issues/{int(created['number'])}/labels",
                body={"labels": list(labels)},
            )
            created["labels"] = [{"name": name} for name in labels]
        return self._pull_request(created)

    @staticmethod
    def _check_repo(repo: str) -> None:
        if not REPO_NAME.fullmatch(repo) or ".." in repo:
            raise RepoProviderError("Refused the repository name.")

    @staticmethod
    def _pull_request(item: dict) -> PullRequest:
        head_repo = (item["head"].get("repo") or {}).get("full_name", "")
        state: PrState = MERGED if item.get("merged_at") else item["state"]
        return PullRequest(
            url=item["html_url"],
            base_repo=item["base"]["repo"]["full_name"],
            head_repo=head_repo,
            head_branch=item["head"]["ref"],
            base_branch=item["base"]["ref"],
            state=state,
            labels=tuple(label["name"] for label in item.get("labels", [])),
            title=item.get("title") or "",
            body=item.get("body") or "",
            draft=bool(item.get("draft")),
        )

    def _call(
        self,
        method: str,
        path: str,
        params: dict[str, str | int] | None = None,
        body: dict | None = None,
    ):
        url = self._base_url + quote(path, safe="/")
        if params:
            url += "?" + urlencode(params)
        request = urllib.request.Request(
            url,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": f"Bearer {self._token.get_secret_value()}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": API_VERSION,
            },
        )
        secrets = (self._token.get_secret_value(),)
        try:
            with _OPENER.open(request, timeout=TIMEOUT_SECONDS) as response:
                return json.load(response)
        except urllib.error.HTTPError as failure:
            detail = failure.read().decode(errors="replace")[:ERROR_DETAIL_MAX_CHARS]
            raise RepoProviderError(
                redact(
                    f"GitHub {method} {path} failed with {failure.code}. {detail}",
                    secrets,
                )
            ) from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as failure:
            raise RepoProviderError(
                redact(f"GitHub {method} {path} failed. {failure}", secrets)
            ) from None
