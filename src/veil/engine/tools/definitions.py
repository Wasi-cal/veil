from veil.engine.constants.tools import FINISH, TOOL_DESCRIPTIONS
from veil.engine.models.llm.tool_definition import ToolDefinition
from veil.engine.models.tool_args.finish_args import FinishArgs
from veil.engine.tools.toolbox import TOOLS


def tool_definitions() -> list[ToolDefinition]:
    """The tools of the model: the four tools of the toolbox, then finish."""
    argument_models = {name: arguments for name, (arguments, _) in TOOLS.items()}
    argument_models[FINISH] = FinishArgs
    return [
        ToolDefinition(
            name=name,
            description=TOOL_DESCRIPTIONS[name],
            parameters=arguments.model_json_schema(),
        )
        for name, arguments in argument_models.items()
    ]
