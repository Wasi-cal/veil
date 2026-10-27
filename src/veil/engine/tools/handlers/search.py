import re

from veil.engine.models.config.settings import Settings
from veil.engine.models.tool_args.search_args import SearchArgs
from veil.engine.tools.handlers.readable import readable_files
from veil.engine.tools.result_cap import NARROW_NOTE
from veil.engine.workspace.working_copy import WorkingCopy


def search(args: SearchArgs, working_copy: WorkingCopy, settings: Settings) -> str:
    try:
        regex = re.compile(args.pattern)
    except re.error as error:
        return f"Error: The pattern is not a valid regular expression. {error}."
    matches: list[str] = []
    for path in readable_files(working_copy, settings):
        try:
            lines = working_copy.read(path).splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            if regex.search(line):
                if len(matches) == settings.search_max_matches:
                    return "\n".join([*matches, NARROW_NOTE])
                matches.append(f"{path}:{number}:{line}")
    return "\n".join(matches) or "No matches."
