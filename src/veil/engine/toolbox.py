import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from veil.engine.constants.tools import EDIT_FILE, LIST_DIR, READ_FILE, SEARCH
from veil.engine.models.edit_file_args import EditFileArgs
from veil.engine.models.list_dir_args import ListDirArgs
from veil.engine.models.read_file_args import ReadFileArgs
from veil.engine.models.search_args import SearchArgs
from veil.engine.models.settings import Settings
from veil.engine.models.tool_call import ToolCall
from veil.engine.path_rules import RuleViolation, check_readable, normalize_dir
from veil.engine.working_copy import EditRejected, WorkingCopy

NARROW_NOTE = "The result is incomplete. Make the request narrower. For example, use a later start line or a more exact pattern."


def _first_problem(error: ValidationError) -> str:
    problem = error.errors()[0]
    field = ".".join(str(part) for part in problem["loc"]) or "arguments"
    return f"Field {field}: {problem['msg']}."


class Toolbox:
    """The tools that the model can call. Each tool returns text to the model. No tool raises an error."""

    def __init__(self, working_copy: WorkingCopy, settings: Settings):
        self._working_copy = working_copy
        self._settings = settings
        self._tools: dict[str, tuple[type[BaseModel], Callable[[Any], str]]] = {
            EDIT_FILE: (EditFileArgs, self._edit_file),
            READ_FILE: (ReadFileArgs, self._read_file),
            SEARCH: (SearchArgs, self._search),
            LIST_DIR: (ListDirArgs, self._list_dir),
        }

    def run(self, call: ToolCall) -> str:
        if call.name not in self._tools:
            return f"Error: The tool {call.name!r} does not exist."
        arguments_model, handler = self._tools[call.name]
        try:
            arguments = arguments_model.model_validate(call.arguments)
        except ValidationError as error:
            return f"Error: The arguments for {call.name} are not valid. {_first_problem(error)}"
        return self._cap(handler(arguments))

    def _edit_file(self, args: EditFileArgs) -> str:
        try:
            self._working_copy.edit(args.path, args.old, args.new)
        except EditRejected as rejected:
            return str(rejected)
        return "Edit applied."

    def _read_file(self, args: ReadFileArgs) -> str:
        try:
            path = self._readable(args.path)
            lines = self._working_copy.read(path).splitlines()
        except RuleViolation as violation:
            return f"Refused: {violation}"
        except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
            return f"Error: {args.path} is not a text file in the repository."
        window = lines[args.start_line - 1 :][: self._settings.read_file_max_lines]
        text = "\n".join(window)
        if args.start_line - 1 + len(window) < len(lines):
            text += f"\n{NARROW_NOTE}"
        return text

    def _search(self, args: SearchArgs) -> str:
        try:
            regex = re.compile(args.pattern)
        except re.error as error:
            return f"Error: The pattern is not a valid regular expression. {error}."
        limit = self._settings.search_max_matches
        matches: list[str] = []
        for path in self._readable_files():
            try:
                lines = self._working_copy.read(path).splitlines()
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(lines, 1):
                if regex.search(line):
                    if len(matches) == limit:
                        return "\n".join([*matches, NARROW_NOTE])
                    matches.append(f"{path}:{number}:{line}")
        return "\n".join(matches) or "No matches."

    def _list_dir(self, args: ListDirArgs) -> str:
        try:
            base = normalize_dir(args.path)
        except RuleViolation as violation:
            return f"Refused: {violation}"
        prefix = f"{base}/" if base else ""
        entries = set()
        for path in self._readable_files():
            if path.startswith(prefix):
                name, slash, _ = path[len(prefix) :].partition("/")
                entries.add(f"{name}/" if slash else name)
        return "\n".join(sorted(entries)) or "The folder has no files."

    def _readable(self, path: str) -> str:
        return check_readable(path, self._settings.extra_refused_read_patterns)

    def _readable_files(self) -> list[str]:
        readable = []
        for path in self._working_copy.list_files():
            try:
                readable.append(self._readable(path))
            except RuleViolation:
                continue
        return readable

    def _cap(self, text: str) -> str:
        limit = self._settings.tool_result_max_bytes
        if len(text.encode()) <= limit:
            return text
        room = limit - len(NARROW_NOTE.encode()) - 1
        return f"{text.encode()[:room].decode(errors='ignore')}\n{NARROW_NOTE}"
