from veil.engine.context import Context
from veil.engine.errors.attempt_failed import AttemptFailed
from veil.engine.models.tool_args.finish_args import FinishArgs
from veil.engine.secrets.scan import find_new_secret, find_secret
from veil.engine.workspace.working_copy import WorkingCopy


def ensure_no_secret(
    context: Context, working_copy: WorkingCopy, finish: FinishArgs
) -> None:
    """Raise AttemptFailed if the Fix adds a secret to a file, to the commit message or to the explanation.

    A secret that was already in a file does not count.
    The reason names the kind of secret and where it is. It never holds the value.
    """
    values = context.credential_values
    for before, after in working_copy.edits():
        found = find_new_secret(before, after, values)
        if found:
            raise _held("The change adds", found)
    for where, text in (
        ("The commit message holds", finish.commit_message),
        ("The explanation holds", finish.explanation),
    ):
        found = find_secret(text, values)
        if found:
            raise _held(where, found)


def _held(where: str, kind: str) -> AttemptFailed:
    return AttemptFailed(f"{where} {kind}. A Fix must never hold a secret.")
