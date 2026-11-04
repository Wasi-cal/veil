from collections.abc import Iterable

from veil.engine.breaking.manifest import manifest_reasons, ticket_jump_reasons
from veil.engine.breaking.public_interface import interface_reasons
from veil.engine.models.ticket.ticket import Ticket


def breaking_reasons(
    changes: Iterable[tuple[str, str, str]], ticket: Ticket | None = None
) -> list[str]:
    """Return the reasons that the Engine finds for a Breaking change, with no model call.

    `changes` holds the path, the old text and the new text of each edited file.
    A package ticket adds a reason when its versions make a major jump and no other reason names the package.
    A check can only add a reason. It never clears a flag that the model set.
    """
    reasons = [
        reason
        for path, before, after in changes
        for reason in (
            *interface_reasons(path, before, after),
            *manifest_reasons(path, before, after),
        )
    ]
    if ticket and ticket.package:
        named = f"The dependency `{ticket.package}`"
        if not any(reason.startswith(named) for reason in reasons):
            reasons += ticket_jump_reasons(
                ticket.file,
                ticket.package,
                ticket.installed_version,
                ticket.fixed_version,
            )
    return reasons
