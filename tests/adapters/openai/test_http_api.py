import pytest
from pydantic import SecretStr

from tests.fakes.http_server import StubHttpServer
from tests.fakes.openai_fixtures import (
    function_call_item,
    message_item,
    reasoning_item,
    response_json,
)
from veil.adapters.openai.http_api import HttpOpenAIApi
from veil.engine.errors.model_client_error import ModelClientError

API_KEY = "".join(["s", "k-", "proj-Zx9Yw8Vu7Ts6Rq5Po4Nm3Lk2Jh1Gf0EdCbA9876543210"])  # noqa: FLY002
RESPONSES = ("POST", "/v1/responses")
INPUT = [{"role": "user", "content": "Fix it."}]
TOOLS = [{"type": "function", "name": "finish", "description": "d", "parameters": {}}]


def api_for(server: StubHttpServer, **options) -> HttpOpenAIApi:
    return HttpOpenAIApi(SecretStr(API_KEY), base_url=server.url, **options)


def create(server: StubHttpServer, **options):
    return api_for(server, **options).create_response("cheap-model", INPUT, TOOLS)


def test_the_request_has_the_model_the_items_the_tools_and_no_storage():
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (200, response_json([]))

        create(server)

    [request] = server.seen
    assert request.body == {
        "model": "cheap-model",
        "input": INPUT,
        "tools": TOOLS,
        "store": False,
    }
    assert request.authorization == f"Bearer {API_KEY}"


def test_the_function_calls_and_the_tokens_come_from_the_reply_and_other_items_are_ignored():
    output = [
        reasoning_item(),
        message_item("Looking."),
        function_call_item("call_a", "read_file", '{"path": "app.py"}'),
        function_call_item("call_b", "search", '{"pattern": "eval"}'),
    ]
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (200, response_json(output))

        reply = create(server)

    assert [(c.call_id, c.name, c.arguments) for c in reply.function_calls] == [
        ("call_a", "read_file", '{"path": "app.py"}'),
        ("call_b", "search", '{"pattern": "eval"}'),
    ]
    assert reply.total_tokens == 120


def test_the_tokens_are_the_sum_when_the_reply_gives_no_total():
    usage = {"input_tokens": 70, "output_tokens": 5}
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (200, response_json([], usage=usage))

        assert create(server).total_tokens == 75


def test_a_reply_with_no_usage_is_an_error_and_never_zero_tokens():
    reply = response_json([])
    del reply["usage"]
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (200, reply)

        with pytest.raises(ModelClientError, match="usage") as error:
            create(server)

    assert error.value.retryable is False


def test_an_incomplete_reply_still_gives_its_calls_and_tokens():
    output = [function_call_item("call_a", "finish", "{}")]
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (
            200,
            response_json(
                output,
                status="incomplete",
                incomplete_details={"reason": "max_output_tokens"},
            ),
        )

        reply = create(server)

    assert [c.call_id for c in reply.function_calls] == ["call_a"]
    assert reply.total_tokens == 120


@pytest.mark.parametrize(
    ("code", "retryable"),
    [("server_error", True), ("rate_limit_exceeded", True), ("invalid_prompt", False)],
)
def test_a_failed_reply_is_an_error_that_says_if_a_retry_can_help(code, retryable):
    failure = {"code": code, "message": f"The call failed. Key {API_KEY} seen."}
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (
            200,
            response_json([], status="failed", error=failure),
        )

        with pytest.raises(ModelClientError) as error:
            create(server)

    assert error.value.retryable is retryable
    assert code in str(error.value)
    assert API_KEY not in str(error.value)


@pytest.mark.parametrize(
    ("status", "retryable"),
    [(429, True), (500, True), (502, True), (503, True), (400, False), (401, False)],
)
def test_an_http_error_names_the_status_hides_the_key_and_says_if_a_retry_can_help(
    status, retryable
):
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (
            status,
            {"error": {"message": f"Bad key {API_KEY}"}},
        )

        with pytest.raises(ModelClientError) as error:
            create(server)

    assert str(status) in str(error.value)
    assert API_KEY not in str(error.value)
    assert error.value.retryable is retryable


def test_a_429_that_says_the_quota_is_gone_is_not_worth_a_retry():
    body = {"error": {"code": "insufficient_quota", "message": "You ran out."}}
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (429, body)

        with pytest.raises(ModelClientError) as error:
            create(server)

    assert error.value.retryable is False


def test_the_tools_are_not_changed_on_the_way_to_the_api():
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (200, response_json([]))

        create(server)

    assert server.seen[0].body["tools"] == TOOLS


def test_a_server_that_is_down_is_a_retryable_error_without_the_key():
    with StubHttpServer() as server:
        api = api_for(server)

    with pytest.raises(ModelClientError) as error:
        api.create_response("cheap-model", INPUT, TOOLS)

    assert error.value.retryable is True
    assert API_KEY not in str(error.value)


def test_a_call_that_takes_longer_than_the_time_out_is_a_retryable_error():
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (200, response_json([]))
        server.delay_seconds = 0.6

        with pytest.raises(ModelClientError) as error:
            create(server, timeout_seconds=0.1)

    assert error.value.retryable is True


def test_a_redirect_never_carries_the_key_to_another_host():
    with StubHttpServer() as elsewhere, StubHttpServer() as server:
        server.routes[RESPONSES] = (
            307,
            {},
            {"Location": f"{elsewhere.url}/v1/responses"},
        )

        with pytest.raises(ModelClientError):
            create(server)

    assert elsewhere.seen == []


@pytest.mark.parametrize("url", ["http://api.example.invalid", "file:///x", "api"])
def test_the_adapter_refuses_a_url_that_is_not_https(url):
    with pytest.raises(ModelClientError):
        HttpOpenAIApi(SecretStr(API_KEY), base_url=url)


@pytest.mark.parametrize(
    "reply",
    [
        {"status": "completed"},
        {"status": "completed", "output": "text", "usage": {"total_tokens": 1}},
        {
            "status": "completed",
            "output": [{"type": "function_call", "call_id": "c"}],
            "usage": {"total_tokens": 1},
        },
        {
            "status": "completed",
            "output": [function_call_item("c", "finish", {"not": "text"})],
            "usage": {"total_tokens": 1},
        },
        [],
    ],
    ids=[
        "no output",
        "output is text",
        "call has no name",
        "arguments not text",
        "list",
    ],
)
def test_a_reply_in_an_unexpected_shape_is_a_tracker_style_error(reply):
    with StubHttpServer() as server:
        server.routes[RESPONSES] = (200, reply)

        with pytest.raises(ModelClientError):
            create(server)


def test_the_key_does_not_show_in_repr():
    api = HttpOpenAIApi(SecretStr(API_KEY), base_url="https://api.example.invalid")

    assert API_KEY not in repr(api)
