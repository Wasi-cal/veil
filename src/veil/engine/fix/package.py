import posixpath

from veil.engine.constants.package import LOCKFILE_MANIFESTS
from veil.engine.models.ticket.ticket import Ticket


def manifest_target(ticket: Ticket) -> Ticket:
    """A package ticket on a lockfile becomes a ticket on the manifest in the same folder.

    The Engine never reads or edits a lockfile. Any other ticket stays as it is.
    """
    if not ticket.package:
        return ticket
    folder, name = posixpath.split(ticket.file.replace("\\", "/"))
    manifest = LOCKFILE_MANIFESTS.get(name.lower())
    if manifest is None:
        return ticket
    return ticket.model_copy(update={"file": posixpath.join(folder, manifest)})
