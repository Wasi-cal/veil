from veil.engine.errors.edit_rejected import EditRejected
from veil.engine.models.config.settings import Settings
from veil.engine.models.tool_args.edit_file_args import EditFileArgs
from veil.engine.workspace.working_copy import WorkingCopy


def edit_file(args: EditFileArgs, working_copy: WorkingCopy, settings: Settings) -> str:
    try:
        working_copy.edit(args.path, args.old, args.new)
    except EditRejected as rejected:
        return str(rejected)
    return "Edit applied."
