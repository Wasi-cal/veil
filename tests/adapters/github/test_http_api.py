import pytest
from pydantic import SecretStr

from tests.adapters.github.support import TOKEN
from tests.fakes.github_fixtures import pull_json
from tests.fakes.http_server import StubHttpServer
from veil.adapters.github.http_api import HttpGitHubApi
from veil.engine.errors.repo_provider_error import RepoProviderError
from veil.engine.errors.token_expired import TokenExpired


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


def test_it_reads_every_pull_request_in_pages_and_never_uses_the_search_api():
    first = [pull_json(n, head=f"b{n}", base="main") for n in range(1, 101)]
    second = [
        pull_json(101, head="veil/fix-GR-5", base="feature-x", labels=("veil-fix",))
    ]
    with StubHttpServer() as server:
        server.routes[("GET", "/repos/acme/app/pulls")] = [(200, first), (200, second)]

        found = api_for(server).find_pull_requests("acme/app")

    assert len(found) == 101
    assert found[-1].labels == ("veil-fix",)
    assert [r.path for r in server.seen] == ["/repos/acme/app/pulls"] * 2
    assert [r.query["page"] for r in server.seen] == [["1"], ["2"]]


def test_it_opens_a_ready_pr_and_puts_the_labels_on_it():
    with StubHttpServer() as server:
        server.routes[("POST", "/repos/acme/app/pulls")] = (
            201,
            pull_json(9, head="veil/fix-GR-1", base="feature-x", draft=False),
        )
        server.routes[("POST", "/repos/acme/app/issues/9/labels")] = (
            200,
            [{"name": "issue-abc"}],
        )

        pr = api_for(server).create_pr(
            "acme/app", "veil/fix-GR-1", "feature-x", "Fix", "Body", ("issue-abc",)
        )

    create, label = server.seen
    assert create.body == {
        "title": "Fix",
        "head": "veil/fix-GR-1",
        "base": "feature-x",
        "body": "Body",
        "draft": False,
    }
    assert label.body == {"labels": ["issue-abc"]}
    assert (pr.url, pr.draft, pr.labels) == (
        "https://github.example.invalid/acme/app/pull/9",
        False,
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


def test_a_401_from_github_is_an_expired_token_error():
    with StubHttpServer() as server:
        server.routes[("GET", "/repos/acme/app/pulls")] = (
            401,
            {"message": "Bad credentials"},
        )

        with pytest.raises(TokenExpired) as failure:
            api_for(server).find_pull_requests("acme/app", head="feature-x")

    assert TOKEN not in str(failure.value)


@pytest.mark.parametrize("status", [403, 404, 422, 500])
def test_any_other_failure_of_github_is_not_an_expired_token(status):
    with StubHttpServer() as server:
        server.routes[("GET", "/repos/acme/app/pulls")] = (status, {"message": "no"})

        with pytest.raises(RepoProviderError) as failure:
            api_for(server).find_pull_requests("acme/app", head="feature-x")

    assert not isinstance(failure.value, TokenExpired)


def test_it_reads_the_default_branch_of_a_repository():
    with StubHttpServer() as server:
        server.routes[("GET", "/repos/acme/app")] = (200, {"default_branch": "trunk"})

        branch = api_for(server).default_branch("acme/app")

    assert branch == "trunk"
    [request] = server.seen
    assert request.authorization == f"Bearer {TOKEN}"


@pytest.mark.parametrize("reply", [{}, {"default_branch": ""}, {"default_branch": 7}])
def test_a_reply_without_a_default_branch_is_an_error(reply):
    with StubHttpServer() as server:
        server.routes[("GET", "/repos/acme/app")] = (200, reply)

        with pytest.raises(RepoProviderError, match="default branch"):
            api_for(server).default_branch("acme/app")


def test_it_refuses_a_bad_repository_name_for_the_default_branch():
    with StubHttpServer() as server:
        with pytest.raises(RepoProviderError):
            api_for(server).default_branch("acme/../app")

        assert server.seen == []
