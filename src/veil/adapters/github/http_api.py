from typing import Any

from pydantic import SecretStr

from veil.adapters.github.constants.http import (
    API_URL,
    API_VERSION,
    PAGE_SIZE,
)
from veil.adapters.github.constants.pr_states import MERGED, PrState
from veil.adapters.github.constants.repo_name import REPO_NAME
from veil.adapters.github.models.pull_request import PullRequest
from veil.adapters.json_http import call_json
from veil.engine.errors.repo_provider_error import RepoProviderError


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
    ) -> Any:
        reply = call_json(
            service="GitHub",
            error=RepoProviderError,
            secrets=(self._token.get_secret_value(),),
            base_url=self._base_url,
            method=method,
            path=path,
            params=params,
            body=body,
            headers={
                "Authorization": f"Bearer {self._token.get_secret_value()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
            },
        )
        if reply is None:
            raise RepoProviderError(f"GitHub {method} {path} gave an empty reply.")
        return reply
