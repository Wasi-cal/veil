from veil.engine.constants.tools import FINISH
from veil.engine.errors.failed_fix import FailedFix
from veil.engine.interfaces.model_client import ModelClient
from veil.engine.models.config.settings import Settings
from veil.engine.models.report.run_report import RunReport
from veil.engine.tools.toolbox import Toolbox


def converse(
    model_client: ModelClient,
    toolbox: Toolbox,
    messages: list[dict],
    settings: Settings,
    report: RunReport,
) -> None:
    """Run the tool calls of the model until it calls `finish`. Raise FailedFix at the step cap."""
    steps = 0
    finished = False
    while not finished:
        reply = model_client.next(messages)
        report.tokens_used += reply.tokens
        steps += 0 if reply.tool_calls else 1  # An empty reply also counts as a step.
        for call in reply.tool_calls:
            steps += 1
            if call.name == FINISH:
                finished = True
                break
            messages.append({"role": "tool", "content": toolbox.run(call)})
            if steps >= settings.step_cap:
                raise _step_cap_reached(settings.step_cap)
        if not finished and steps >= settings.step_cap:
            raise _step_cap_reached(settings.step_cap)


def _step_cap_reached(cap: int) -> FailedFix:
    return FailedFix(
        f"The attempt used {cap} tool calls and did not finish. This is the step cap."
    )
