from veil.engine.constants.names import FIXED_BRANCH_PREFIXES
from veil.engine.models.config.settings import Settings


def is_fix_branch(branch: str | None, settings: Settings) -> bool:
    """True when the branch is one of the Fix branches of veil.

    A Fix branch starts with a fixed prefix or with the prefix of the setting `branch_prefix`.
    Veil never runs on its own branches. A run there could only fix its own work again.
    """
    return bool(branch) and branch.startswith(
        (*FIXED_BRANCH_PREFIXES, settings.branch_prefix)
    )
