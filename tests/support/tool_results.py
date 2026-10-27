from tests.fakes import finish
from tests.support.scenario import GOOD_EDIT, VULNERABLE, make_context
from veil.engine import run


def results_for(tmp_path, calls, files):
    """Run one Fix attempt. Return the result that the model gets for each call in `calls`."""
    script = [[call] for call in calls] + [[GOOD_EDIT], [finish("Fixed.")]]
    context, _, _, model = make_context(
        tmp_path, script, files={"app.py": VULNERABLE, **files}
    )
    run(context)
    return [model.received[i + 1][-1]["content"] for i in range(len(calls))]
