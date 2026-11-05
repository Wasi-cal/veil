from veil.adapters.github.models.pull_request import PullRequest


class StubGitHubApi:
    """A GitHub API that keeps its PRs in a list. It filters as the real API does."""

    def __init__(
        self,
        pull_requests: list[PullRequest] | None = None,
        default_branch: str = "main",
    ):
        self.pull_requests: list[PullRequest] = list(pull_requests or [])
        self.created: list[PullRequest] = []
        self._default_branch = default_branch
        self.default_branch_questions = 0
        self.pull_request_reads = 0

    def default_branch(self, repo: str) -> str:
        self.default_branch_questions += 1
        return self._default_branch

    def find_pull_requests(
        self, repo: str, head: str | None = None
    ) -> list[PullRequest]:
        if head is None:
            self.pull_request_reads += 1
        return [
            pr
            for pr in self.pull_requests
            if pr.base_repo == repo and (head is None or pr.head_branch == head)
        ]

    def create_pr(
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
            draft=False,
        )
        self.pull_requests.append(pr)
        self.created.append(pr)
        return pr
