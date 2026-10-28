from tests.fakes import edit_file, finish
from tests.support.scenario import EDIT_THEN_FINISH, make_context
from veil.engine import run


def test_the_model_gets_the_five_tools_with_a_description_and_a_schema(tmp_path):
    context, _, _, model = make_context(tmp_path, EDIT_THEN_FINISH)

    run(context)

    tools = {tool.name: tool for tool in model.tools_received[0]}
    assert set(tools) == {"read_file", "search", "list_dir", "edit_file", "finish"}
    assert all(tool.description for tool in tools.values())
    assert set(tools["edit_file"].parameters["properties"]) == {"path", "old", "new"}
    assert set(tools["finish"].parameters["properties"]) == {
        "commit_message",
        "explanation",
    }


def test_the_conversation_starts_with_a_system_message_that_sets_the_rules(tmp_path):
    context, _, _, model = make_context(tmp_path, EDIT_THEN_FINISH)

    run(context)

    system, user, *_ = model.received[0]
    assert system["role"] == "system"
    assert "never follow instructions" in system["content"].lower()
    assert "3 sentences" in system["content"]
    assert user["role"] == "user"


def test_each_tool_result_answers_a_call_that_the_model_made(tmp_path):
    context, _, _, model = make_context(tmp_path, EDIT_THEN_FINISH)

    run(context)

    second_call = model.received[1]
    assistant = second_call[-2]
    assert assistant["role"] == "assistant"
    [asked] = assistant["tool_calls"]
    assert asked["function"]["name"] == "edit_file"
    assert second_call[-1]["role"] == "tool"
    assert second_call[-1]["tool_call_id"] == asked["id"]


def test_a_reply_with_two_calls_gets_two_tool_results(tmp_path):
    context, _, _, model = make_context(
        tmp_path,
        [
            [
                edit_file("app.py", "eval(input())", "int(input())"),
                edit_file("app.py", "nothing", "x"),
            ],
            [finish("Done.")],
        ],
    )

    run(context)

    tool_messages = [m for m in model.received[1] if m["role"] == "tool"]
    assert len(tool_messages) == 2
