from veil.engine.errors.rule_violation import RuleViolation
from veil.engine.models.config.settings import Settings
from veil.engine.workspace.path_rules import check_readable
from veil.engine.workspace.working_copy import WorkingCopy


def readable_path(path: str, settings: Settings) -> str:
    return check_readable(path, settings.extra_refused_read_patterns)


def readable_files(working_copy: WorkingCopy, settings: Settings) -> list[str]:
    """The files that the model may read."""
    readable = []
    for path in working_copy.list_files():
        try:
            readable.append(readable_path(path, settings))
        except RuleViolation:
            continue
    return readable
