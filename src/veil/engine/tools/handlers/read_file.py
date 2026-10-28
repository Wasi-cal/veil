from veil.engine.constants.tool_messages import NARROW_NOTE
from veil.engine.errors.rule_violation import RuleViolation
from veil.engine.models.config.settings import Settings
from veil.engine.models.tool_args.read_file_args import ReadFileArgs
from veil.engine.tools.handlers.readable import readable_path
from veil.engine.workspace.working_copy import WorkingCopy


def read_file(args: ReadFileArgs, working_copy: WorkingCopy, settings: Settings) -> str:
    try:
        path = readable_path(args.path, settings)
        lines = working_copy.read(path).splitlines()
    except RuleViolation as violation:
        return f"Refused: {violation}"
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        return f"Error: {args.path} is not a text file in the repository."
    window = lines[args.start_line - 1 :][: settings.read_file_max_lines]
    text = "\n".join(window)
    if args.start_line - 1 + len(window) < len(lines):
        text += f"\n{NARROW_NOTE}"
    return text
