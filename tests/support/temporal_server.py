"""A throwaway Temporal dev server for tests. It runs from the temporal program on this machine."""

import shutil
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

START_WAIT_SECONDS = 30.0


def find_temporal() -> str | None:
    """The path of the temporal program, from PATH."""
    return shutil.which("temporal")


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@contextmanager
def running_temporal() -> Iterator[str]:
    """Start a dev server with no UI and no disk store. Yield its host and port. Stop it at the end."""
    program = find_temporal()
    if program is None:
        raise RuntimeError("No temporal program on this machine.")
    port = _free_port()
    folder = Path(tempfile.mkdtemp(prefix="veil-temporal-"))
    process = subprocess.Popen(
        [
            program,
            "server",
            "start-dev",
            "--ip",
            "127.0.0.1",
            "--port",
            str(port),
            "--headless",
            "--log-level",
            "error",
        ],
        stdout=(folder / "log").open("a"),
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + START_WAIT_SECONDS
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            with suppress(OSError), socket.create_connection(("127.0.0.1", port), 0.2):
                time.sleep(0.5)
                yield f"127.0.0.1:{port}"
                return
            time.sleep(0.1)
        raise RuntimeError(
            f"Temporal did not start. Log: {(folder / 'log').read_text()[-1500:]}"
        )
    finally:
        process.terminate()
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=5)
        if process.poll() is None:
            process.kill()
        shutil.rmtree(folder, ignore_errors=True)
