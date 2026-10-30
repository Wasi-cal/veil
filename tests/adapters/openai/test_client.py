import json

import pytest

from tests.fakes.openai_api import StubOpenAIApi, api_reply
from tests.support.scenario import FIXED, make_context
from veil.adapters.openai.client import OpenAIModelClient
from veil.engine import ToolDefinition, run
from veil.engine.errors.model_client_error import ModelClientError

TOOLS = [
    ToolDefinition(
        name="read_file",
        description="Read a file.",
        parameters={"type": "object", "properties": {"path": {"type": "string"}}},
    )
]
MESSAGES = [
    {"role": "system", "content": "Fix one finding."},
    {"role": "user", "content": "The finding is in app.py."},
]


def client_with(*replies):
    api = StubOpenAIApi(list(replies))
    return OpenAIModelClient(api), api


def test_the_reply_has_each_call_with_the_id_of_the_api_and_the_tokens_it_counted():
    client, _ = client_with(
        api_reply(
            ("call_a", "read_file", '{"path": "app.py"}'),
            ("call_b", "search", '{"pattern": "eval"}'),
            tokens=137,
        )
    )

    reply = client.next(MESSAGES, "cheap-model", TOOLS)

    assert [(c.id, c.name, c.arguments) for c in reply.tool_calls] == [
        ("call_a", "read_file", {"path": "app.py"}),
        ("call_b", "search", {"pattern": "eval"}),
    ]
    assert reply.tokens == 137


def test_the_model_name_and_the_tools_go_to_the_api_in_the_responses_shape():
    client, api = client_with(api_reply())

    client.next(MESSAGES, "strong-model", TOOLS)

    [request] = api.requests
    assert request["model"] == "strong-model"
    assert request["tools"] == [
        {
            "type": "function",
            "strict": False,
            "name": "read_file",
            "description": "Read a file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        }
    ]


def test_the_conversation_goes_to_the_api_as_items_and_each_answer_names_its_call():
    conversation = [
        *MESSAGES,
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_a",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": '{"path": "a.py"}'},
                },
                {
                    "id": "call_b",
                    "type": "function",
                    "function": {"name": "search", "arguments": '{"pattern": "x"}'},
                },
            ],
        },
        {"role": "tool", "tool_call_id": "call_a", "content": "file text"},
        {"role": "tool", "tool_call_id": "call_b", "content": "no match"},
    ]
    client, api = client_with(api_reply())

    client.next(conversation, "cheap-model", TOOLS)

    assert api.requests[0]["input"] == [
        {"role": "system", "content": "Fix one finding."},
        {"role": "user", "content": "The finding is in app.py."},
        {
            "type": "function_call",
            "call_id": "call_a",
            "name": "read_file",
            "arguments": '{"path": "a.py"}',
        },
        {
            "type": "function_call",
            "call_id": "call_b",
            "name": "search",
            "arguments": '{"pattern": "x"}',
        },
        {"type": "function_call_output", "call_id": "call_a", "output": "file text"},
        {"type": "function_call_output", "call_id": "call_b", "output": "no match"},
    ]


@pytest.mark.parametrize("written", ["{not json", "[1, 2]", "null", '"text"', ""])
def test_arguments_that_are_not_a_json_object_become_a_call_with_no_arguments(
    written,
):
    client, _ = client_with(api_reply(("call_a", "edit_file", written)))

    [call] = client.next(MESSAGES, "cheap-model", TOOLS).tool_calls

    assert (call.id, call.name, call.arguments) == ("call_a", "edit_file", {})


def test_a_reply_with_no_call_has_no_tool_calls_and_still_counts_tokens():
    client, _ = client_with(api_reply(tokens=55))

    reply = client.next(MESSAGES, "cheap-model", TOOLS)

    assert reply.tool_calls == []
    assert reply.tokens == 55


def test_a_tool_message_that_answers_no_call_is_a_clear_error_and_nothing_is_sent():
    conversation = [
        *MESSAGES,
        {"role": "tool", "tool_call_id": "call_x", "content": "text"},
    ]
    client, api = client_with(api_reply())

    with pytest.raises(ModelClientError, match="answers no call") as error:
        client.next(conversation, "cheap-model", TOOLS)

    assert error.value.retryable is False
    assert api.requests == []


def test_an_error_of_the_api_reaches_the_caller_unchanged():
    error = ModelClientError("The API refused the key.", retryable=False)
    client, _ = client_with(error)

    with pytest.raises(ModelClientError) as raised:
        client.next(MESSAGES, "cheap-model", TOOLS)

    assert raised.value is error


def test_the_engine_fixes_a_ticket_with_the_real_client_and_counts_the_api_tokens(
    tmp_path,
):
    edit = json.dumps({"path": "app.py", "old": "eval(input())", "new": "int(input())"})
    finish = json.dumps(
        {"commit_message": "Replace eval.", "explanation": "Used int instead of eval."}
    )
    api = StubOpenAIApi(
        [
            api_reply(("call_1", "edit_file", edit), tokens=11),
            api_reply(("call_2", "finish", finish), tokens=22),
        ]
    )
    context, _, repos, _ = make_context(tmp_path, [])
    context = context.model_copy(update={"model_client": OpenAIModelClient(api)})

    report = run(context)

    assert report.outcomes == {"GR-100": "fixed"}
    assert report.tokens_used == 33
    [pr] = repos.pull_requests
    assert repos.file_on(pr, "app.py") == FIXED
    answers = [
        i for i in api.requests[1]["input"] if i.get("type") == "function_call_output"
    ]
    assert [a["call_id"] for a in answers] == ["call_1"]
