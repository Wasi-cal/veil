"""OpenAI Responses API answers. The fields follow the public API reference and the function calling guide.

These are written by hand. They are not recorded from a live call.
"""


def function_call_item(call_id: str, name: str, arguments: str) -> dict:
    return {
        "id": f"fc_{call_id}",
        "type": "function_call",
        "status": "completed",
        "call_id": call_id,
        "name": name,
        "arguments": arguments,
    }


def message_item(text: str) -> dict:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }


def reasoning_item() -> dict:
    return {"id": "rs_1", "type": "reasoning", "summary": []}


def response_json(
    output: list[dict],
    usage: dict | None = None,
    status: str = "completed",
    error: dict | None = None,
    incomplete_details: dict | None = None,
) -> dict:
    return {
        "id": "resp_1",
        "object": "response",
        "status": status,
        "error": error,
        "incomplete_details": incomplete_details,
        "output": output,
        "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
        if usage is None
        else usage,
    }
