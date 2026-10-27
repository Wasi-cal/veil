from veil.engine.errors.rule_violation import RuleViolation
from veil.engine.models.config.settings import Settings
from veil.engine.models.tool_args.list_dir_args import ListDirArgs
from veil.engine.tools.handlers.readable import readable_files
from veil.engine.workspace.path_rules import normalize_dir
from veil.engine.workspace.working_copy import WorkingCopy


def list_dir(args: ListDirArgs, working_copy: WorkingCopy, settings: Settings) -> str:
    try:
        base = normalize_dir(args.path)
    except RuleViolation as violation:
        return f"Refused: {violation}"
    prefix = f"{base}/" if base else ""
    entries = set()
    for path in readable_files(working_copy, settings):
        if path.startswith(prefix):
            name, slash, _ = path[len(prefix) :].partition("/")
            entries.add(f"{name}/" if slash else name)
    return "\n".join(sorted(entries)) or "The folder has no files."
