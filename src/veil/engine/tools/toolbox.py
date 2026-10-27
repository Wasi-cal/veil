from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from veil.engine.constants.tools import EDIT_FILE, LIST_DIR, READ_FILE, SEARCH
from veil.engine.models.config.settings import Settings
from veil.engine.models.llm.tool_call import ToolCall
from veil.engine.models.tool_args.edit_file_args import EditFileArgs
from veil.engine.models.tool_args.list_dir_args import ListDirArgs
from veil.engine.models.tool_args.read_file_args import ReadFileArgs
from veil.engine.models.tool_args.search_args import SearchArgs
from veil.engine.tools.handlers.edit_file import edit_file
from veil.engine.tools.handlers.list_dir import list_dir
from veil.engine.tools.handlers.read_file import read_file
from veil.engine.tools.handlers.search import search
from veil.engine.tools.result_cap import cap_result
from veil.engine.workspace.working_copy import WorkingCopy

Handler = Callable[[Any, WorkingCopy, Settings], str]

TOOLS: dict[str, tuple[type[BaseModel], Handler]] = {
    EDIT_FILE: (EditFileArgs, edit_file),
    READ_FILE: (ReadFileArgs, read_file),
    SEARCH: (SearchArgs, search),
    LIST_DIR: (ListDirArgs, list_dir),
}


class Toolbox:
    """The tools that the model can call. Each tool returns text to the model. No tool raises an error."""

    def __init__(self, working_copy: WorkingCopy, settings: Settings):
        self._working_copy = working_copy
        self._settings = settings

    def run(self, call: ToolCall) -> str:
        if call.name not in TOOLS:
            return f"Error: The tool {call.name!r} does not exist."
        arguments_model, handler = TOOLS[call.name]
        try:
            arguments = arguments_model.model_validate(call.arguments)
        except ValidationError as error:
            return f"Error: The arguments for {call.name} are not valid. {_first_problem(error)}"
        result = handler(arguments, self._working_copy, self._settings)
        return cap_result(result, self._settings.tool_result_max_bytes)


def _first_problem(error: ValidationError) -> str:
    problem = error.errors()[0]
    field = ".".join(str(part) for part in problem["loc"]) or "arguments"
    return f"Field {field}: {problem['msg']}."
