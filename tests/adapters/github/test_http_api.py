import pytest
from pydantic import SecretStr

from tests.adapters.github.support import TOKEN
from tests.fakes.github_fixtures import pull_json
from tests.fakes.http_server import StubHttpServer
from veil.adapters.github.http_api import HttpGitHubApi
from veil.engine.errors.repo_provider_error import RepoProviderError


def api_for(server: StubHttpServer) -> HttpGitHubApi:
    return HttpGitHubApi(SecretStr(TOKEN), base_url=server.url)


def test_it_finds_the_pull_requests_of_a_head_branch_in_every_state():
    with StubHttpServer() as server:
        server.routes[("GET", "/repos/acme/app/pulls")] = (
            200,
            [
                pull_json(1),
                pull_json(2, state="closed", merged=True),
                pull_json(3, state="closed"),
                pull_json(4, head_repo="fork/app"),
            ],
        )

        found = api_for(server).find_pull_requests("acme/app", head="feature-x")

    assert [(pr.state, pr.head_repo) for pr in found] == [
        ("open", "acme/app"),
        ("merged", "acme/app"),
        ("closed", "acme/app"),
        ("open", "fork/app"),
    ]
    [request] = server.seen
    assert request.query["state"] == ["all"]
    assert request.query["head"] == ["acme:feature-x"]
    assert request.authorization == f"Bearer {TOKEN}"


def test_it_finds_the_pull_requests_that_carry_a_label():
    with StubHttpServer() as server:
        server.routes[("GET", "/search/issues")] = (200, {"items": [{"number": 7}]})
        server.routes[("GET", "/repos/acme/app/pulls/7")] = (
            200,
            pull_json(7, head="gozu/fix-GR-5", base="feature-x", labels=("issue-abc",)),
        )

        [pr] = api_for(server).find_pull_requests("acme/app", label="issue-abc")

    assert (pr.head_branch, pr.base_branch, pr.labels) == (
        "gozu/fix-GR-5",
        "feature-x",
        ("issue-abc",),
    )
    search = server.seen[0]
    assert search.query["q"] == ['repo:acme/app is:pr label:"issue-abc"']


def test_it_opens_a_draft_pr_and_puts_the_labels_on_it():
    with StubHttpServer() as server:
        server.routes[("POST", "/repos/acme/app/pulls")] = (
            201,
            pull_json(9, head="gozu/fix-GR-1", base="feature-x", draft=True),
        )
        server.routes[("POST", "/repos/acme/app/issues/9/labels")] = (
            200,
            [{"name": "issue-abc"}],
        )

        pr = api_for(server).create_draft_pr(
            "acme/app", "gozu/fix-GR-1", "feature-x", "Fix", "Body", ("issue-abc",)
        )

    create, label = server.seen
    assert create.body == {
        "title": "Fix",
        "head": "gozu/fix-GR-1",
        "base": "feature-x",
        "body": "Body",
        "draft": True,
    }
    assert label.body == {"labels": ["issue-abc"]}
    assert (pr.url, pr.draft, pr.labels) == (
        "https://github.example.invalid/acme/app/pull/9",
        True,
        ("issue-abc",),
    )


def test_an_api_error_raises_without_the_token():
    with StubHttpServer() as server:
        server.routes[("GET", "/repos/acme/app/pulls")] = (
            401,
            {"message": f"Bad credentials {TOKEN}"},
        )

        with pytest.raises(RepoProviderError) as error:
            api_for(server).find_pull_requests("acme/app", head="feature-x")

    assert "401" in str(error.value)
    assert TOKEN not in str(error.value)


@pytest.mark.parametrize("repo", ["acme", "acme/app/extra", "../x/y", "acme/a b"])
def test_it_refuses_a_repository_name_that_could_change_the_url(repo):
    with StubHttpServer() as server, pytest.raises(RepoProviderError):
        api_for(server).find_pull_requests(repo, head="x")

    assert server.seen == []


def test_a_redirect_never_carries_the_token_to_another_host():
    with StubHttpServer() as elsewhere, StubHttpServer() as server:
        server.routes[("GET", "/repos/acme/app/pulls")] = (
            302,
            {},
            {"Location": f"{elsewhere.url}/repos/acme/app/pulls"},
        )

        with pytest.raises(RepoProviderError):
            api_for(server).find_pull_requests("acme/app", head="feature-x")

    assert elsewhere.seen == []


@pytest.mark.parametrize("url", ["http://api.example.invalid", "file:///x", "api"])
def test_the_adapter_refuses_a_url_that_is_not_https(url):
    with pytest.raises(RepoProviderError):
        HttpGitHubApi(SecretStr(TOKEN), base_url=url)
