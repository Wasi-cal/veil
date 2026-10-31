import pytest

from tests.fakes.openai_api import StubOpenAIApi, api_reply
from veil.adapters.openai.client import OpenAIModelClient
from veil.engine.errors.model_client_error import ModelClientError

FINISH = (
    "c1",
    "finish",
    '{"commit_message": "x", "problem": "p", "change": "c", "solves": "s"}',
)


def client_for(*replies):
    api = StubOpenAIApi(list(replies))
    pauses: list[float] = []
    return OpenAIModelClient(api, sleep=pauses.append), api, pauses


def call(client):
    return client.next([{"role": "user", "content": "go"}], "model-a", [])


def test_a_retryable_failure_is_tried_again_and_the_reply_counts_once():
    client, api, pauses = client_for(
        ModelClientError("slow down", retryable=True), api_reply(FINISH, tokens=42)
    )

    reply = call(client)

    assert reply.tokens == 42
    assert len(api.requests) == 2
    assert len(pauses) == 1 and pauses[0] > 0


def test_a_permanent_failure_stops_at_once_with_no_pause():
    client, api, pauses = client_for(
        ModelClientError("no quota", retryable=False), api_reply(FINISH)
    )

    with pytest.raises(ModelClientError, match="no quota") as failure:
        call(client)

    assert failure.value.retryable is False
    assert len(api.requests) == 1
    assert pauses == []


def test_the_retry_is_bounded_and_the_pauses_grow_to_a_cap():
    errors = [ModelClientError(f"fail {n}", retryable=True) for n in range(10)]
    client, api, pauses = client_for(*errors)

    with pytest.raises(ModelClientError, match="fail 2") as failure:
        call(client)

    assert failure.value.retryable is True
    assert len(api.requests) == 3
    assert pauses == sorted(pauses)
    assert pauses[0] < pauses[1]
    assert max(pauses) <= 8


def test_a_call_that_works_the_first_time_never_pauses():
    client, api, pauses = client_for(api_reply(FINISH))

    call(client)

    assert (len(api.requests), pauses) == (1, [])
