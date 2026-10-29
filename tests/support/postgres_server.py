"""A throwaway PostgreSQL server for tests. It runs from the PostgreSQL programs on this machine."""

import glob
import os
import shutil
import socket
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SEARCH_PATTERNS = (
    "/opt/homebrew/opt/postgresql@*/bin",
    "/usr/local/opt/postgresql@*/bin",
    "/usr/lib/postgresql/*/bin",
)
SERVER_USER = "veil"
# macOS stops the server at start without a valid locale. The C locale exists everywhere.
ENVIRONMENT = {**os.environ, "LC_ALL": "C"}


def find_program(name: str) -> str | None:
    """The path of a PostgreSQL program, from PATH or from the usual install folders."""
    found = shutil.which(name)
    if found:
        return found
    for pattern in SEARCH_PATTERNS:
        for folder in sorted(glob.glob(pattern), reverse=True):
            candidate = Path(folder) / name
            if candidate.exists():
                return str(candidate)
    return None


def _run(command: list[str]) -> None:
    """Run a PostgreSQL program. If it fails, the error says what the program printed."""
    result = subprocess.run(
        command, capture_output=True, text=True, env=ENVIRONMENT, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{Path(command[0]).name} failed. {result.stderr or result.stdout}"
        )


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@contextmanager
def running_server() -> Iterator[str]:
    """Start an empty server in a temporary folder. Give its admin URL. Stop it and delete the folder at the end.

    If the server does not start, the error holds the log of the server.
    """
    initdb, pg_ctl = find_program("initdb"), find_program("pg_ctl")
    if not initdb or not pg_ctl:
        raise FileNotFoundError(
            "The PostgreSQL programs initdb and pg_ctl are not installed."
        )
    # A short path, because a socket path cannot be longer than about 100 characters.
    root = Path(tempfile.mkdtemp(prefix="vpg", dir="/tmp"))
    data, log = root / "data", root / "log"
    port = _free_port()
    options = f"-p {port} -c listen_addresses=127.0.0.1 -c fsync=off -c unix_socket_directories={root}"
    try:
        _run(
            [initdb, "-D", str(data), "-U", SERVER_USER, "-A", "trust", "-E", "UTF8"]
            + ["--no-sync", "--locale=C"]
        )
        try:
            _run(
                [pg_ctl, "-D", str(data), "-o", options, "-l", str(log), "-w", "start"]
            )
        except RuntimeError as failure:
            tail = log.read_text()[-2000:] if log.exists() else "No log."
            raise RuntimeError(f"{failure} Server log: {tail}") from None
        try:
            yield f"postgresql+psycopg://{SERVER_USER}@127.0.0.1:{port}/postgres"
        finally:
            _run([pg_ctl, "-D", str(data), "-m", "immediate", "-w", "stop"])
    finally:
        shutil.rmtree(root, ignore_errors=True)
