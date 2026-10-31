import json
from collections.abc import Callable

from veil.engine.constants.tools import FINISH
from veil.engine.errors.attempt_failed import AttemptFailed
from veil.engine.fix.budget import ensure_budget
from veil.engine.fix.finish import read_finish
from veil.engine.interfaces.model_client import ModelClient
from veil.engine.models.config.settings import Settings
from veil.engine.models.llm.model_reply import ModelReply
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.tool_args.finish_args import FinishArgs
from veil.engine.tools.definitions import tool_definitions
from veil.engine.tools.toolbox import Toolbox


def converse(
    model_client: ModelClient,
    model: str,
    toolbox: Toolbox,
    messages: list[dict],
    settings: Settings,
    report: RunReport,
    progress: Callable[[int], None] | None = None,
    finding_text: str = "",
) -> FinishArgs:
    """Run the tool calls of the model until it calls finish with valid arguments. Return them.

    A finish call that breaks the format gets an error text, and the model can try again.
    `finding_text` is the text of the ticket. A part that copies it breaks the format.
    Raise AttemptFailed at the step cap. Raise BudgetExhausted before a model call if the run used its token ceiling.
    """
    tools = tool_definitions()
    steps = 0
    finish: FinishArgs | None = None
    while finish is None:
        ensure_budget(report, settings)
        reply = model_client.next(messages, model, tools)
        report.tokens_used += reply.tokens
        if progress is not None:
            progress(report.tokens_used)
        if reply.tool_calls:
            messages.append(_assistant_message(reply))
        steps += 0 if reply.tool_calls else 1  # An empty reply also counts as a step.
        for call in reply.tool_calls:
            steps += 1
            if call.name == FINISH:
                result = read_finish(call, settings, finding_text)
                if isinstance(result, FinishArgs):
                    finish = result
                    break
                messages.append(_tool_message(call.id, result))
            else:
                messages.append(_tool_message(call.id, toolbox.run(call)))
            if steps >= settings.step_cap:
                raise _step_cap_reached(settings.step_cap)
        if finish is None and steps >= settings.step_cap:
            raise _step_cap_reached(settings.step_cap)
    return finish


def _step_cap_reached(cap: int) -> AttemptFailed:
    return AttemptFailed(
        f"The attempt used {cap} tool calls and did not finish. This is the step cap."
    )


def _assistant_message(reply: ModelReply) -> dict:
    """The message that records the calls of the model, in the chat format."""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.arguments),
                },
            }
            for call in reply.tool_calls
        ],
    }


def _tool_message(call_id: str, content: str) -> dict:
    return {"role": "tool", "tool_call_id": call_id, "content": content}
