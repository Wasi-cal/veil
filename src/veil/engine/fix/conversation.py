from veil.engine.constants.tools import FINISH
from veil.engine.errors.attempt_failed import AttemptFailed
from veil.engine.fix.budget import ensure_budget
from veil.engine.fix.finish import read_finish
from veil.engine.interfaces.model_client import ModelClient
from veil.engine.models.config.settings import Settings
from veil.engine.models.report.run_report import RunReport
from veil.engine.models.tool_args.finish_args import FinishArgs
from veil.engine.tools.toolbox import Toolbox


def converse(
    model_client: ModelClient,
    model: str,
    toolbox: Toolbox,
    messages: list[dict],
    settings: Settings,
    report: RunReport,
) -> FinishArgs:
    """Run the tool calls of the model until it calls finish with valid arguments. Return them.

    A finish call that breaks the format gets an error text, and the model can try again.
    Raise AttemptFailed at the step cap. Raise BudgetExhausted before a model call if the run used its token ceiling.
    """
    steps = 0
    finish: FinishArgs | None = None
    while finish is None:
        ensure_budget(report, settings)
        reply = model_client.next(messages, model)
        report.tokens_used += reply.tokens
        steps += 0 if reply.tool_calls else 1  # An empty reply also counts as a step.
        for call in reply.tool_calls:
            steps += 1
            if call.name == FINISH:
                result = read_finish(call, settings)
                if isinstance(result, FinishArgs):
                    finish = result
                    break
                messages.append({"role": "tool", "content": result})
            else:
                messages.append({"role": "tool", "content": toolbox.run(call)})
            if steps >= settings.step_cap:
                raise _step_cap_reached(settings.step_cap)
        if finish is None and steps >= settings.step_cap:
            raise _step_cap_reached(settings.step_cap)
    return finish


def _step_cap_reached(cap: int) -> AttemptFailed:
    return AttemptFailed(
        f"The attempt used {cap} tool calls and did not finish. This is the step cap."
    )
