from veil.adapters.github.models.pull_request import PullRequest


class StubGitHubApi:
    """A GitHub API that keeps its PRs in a list. It filters as the real API does."""

    def __init__(self, pull_requests: list[PullRequest] | None = None):
        self.pull_requests: list[PullRequest] = list(pull_requests or [])
        self.created: list[PullRequest] = []

    def find_pull_requests(
        self, repo: str, head: str | None = None, label: str | None = None
    ) -> list[PullRequest]:
        return [
            pr
            for pr in self.pull_requests
            if pr.base_repo == repo
            and (head is None or pr.head_branch == head)
            and (label is None or label in pr.labels)
        ]

    def create_draft_pr(
        self,
        repo: str,
        head: str,
        base: str,
        title: str,
        body: str,
        labels: tuple[str, ...],
    ) -> PullRequest:
        pr = PullRequest(
            url=f"https://github.example.invalid/{repo}/pull/{len(self.pull_requests) + 1}",
            base_repo=repo,
            head_repo=repo,
            head_branch=head,
            base_branch=base,
            state="open",
            labels=labels,
            title=title,
            body=body,
            draft=True,
        )
        self.pull_requests.append(pr)
        self.created.append(pr)
        return pr
