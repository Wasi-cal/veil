import shutil
import time
from datetime import timedelta
from pathlib import Path


def sweep_old_checkouts(root: Path, older_than: timedelta) -> list[str]:
    """Delete each checkout directory in `root` that is older than the limit. Return their names.

    A worker calls this at start. It cleans up after a crash that skipped the `finally` step.
    It never follows a link and never deletes a plain file.
    """
    if not root.is_dir():
        return []
    limit = time.time() - older_than.total_seconds()
    deleted: list[str] = []
    for entry in sorted(root.iterdir()):
        if entry.is_symlink() or not entry.is_dir():
            continue
        if entry.stat().st_mtime < limit:
            shutil.rmtree(entry, ignore_errors=True)
            deleted.append(entry.name)
    return deleted
