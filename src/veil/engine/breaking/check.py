from collections.abc import Iterable

from veil.engine.breaking.manifest import manifest_reasons
from veil.engine.breaking.public_interface import interface_reasons


def breaking_reasons(changes: Iterable[tuple[str, str, str]]) -> list[str]:
    """Return the reasons that the Engine finds for a Breaking change, with no model call.

    `changes` holds the path, the old text and the new text of each edited file.
    A check can only add a reason. It never clears a flag that the model set.
    """
    return [
        reason
        for path, before, after in changes
        for reason in (
            *interface_reasons(path, before, after),
            *manifest_reasons(path, before, after),
        )
    ]
