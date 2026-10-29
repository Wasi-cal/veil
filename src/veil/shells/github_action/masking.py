from typing import TextIO


def mask_values(values: tuple[str, ...], out: TextIO) -> None:
    """Ask the runner to hide each value in every later log line.

    The runner masks one line at a time, so a value with many lines gets one command per line.
    The runner reads % in a command as an escape, so the command escapes it.
    """
    for value in values:
        for line in value.splitlines():
            if line.strip():
                escaped = line.replace("%", "%25")
                print(f"::add-mask::{escaped}", file=out, flush=True)
