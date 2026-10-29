"""A throwaway Redis server for tests. It runs from the redis-server program on this machine."""

import shutil
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

import redis

SEARCH_FOLDERS = ("/opt/homebrew/opt/redis/bin", "/usr/local/opt/redis/bin", "/usr/bin")
START_WAIT_SECONDS = 5.0


def find_redis_server() -> str | None:
    """The path of redis-server, from PATH or from the usual install folders."""
    found = shutil.which("redis-server")
    if found:
        return found
    for folder in SEARCH_FOLDERS:
        candidate = Path(folder) / "redis-server"
        if candidate.exists():
            return str(candidate)
    return None


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class RunningRedis:
    """One Redis server. A test can stop it and start it again on the same port."""

    def __init__(self, program: str, folder: Path, port: int):
        self._program = program
        self._folder = folder
        self.port = port
        self.url = f"redis://127.0.0.1:{port}/0"
        self._process: subprocess.Popen | None = None

    def start(self) -> None:
        self._process = subprocess.Popen(
            [
                self._program,
                "--port",
                str(self.port),
                "--bind",
                "127.0.0.1",
                "--save",
                "",
                "--appendonly",
                "no",
                "--dir",
                str(self._folder),
            ],
            stdout=(self._folder / "log").open("a"),
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + START_WAIT_SECONDS
        while time.monotonic() < deadline:
            with suppress(redis.RedisError):
                if redis.Redis.from_url(self.url).ping():
                    return
            time.sleep(0.05)
        self.stop()
        log = (self._folder / "log").read_text()[-1500:]
        raise RuntimeError(f"Redis did not start. Log: {log}")

    def stop(self) -> None:
        if self._process is not None:
            self._process.terminate()
            with suppress(subprocess.TimeoutExpired):
                self._process.wait(timeout=5)
            if self._process.poll() is None:
                self._process.kill()
            self._process = None


@contextmanager
def running_redis() -> Iterator[RunningRedis]:
    """Start a Redis server in a temporary folder. Stop it and delete the folder at the end."""
    program = find_redis_server()
    if program is None:
        raise FileNotFoundError("The program redis-server is not installed.")
    folder = Path(tempfile.mkdtemp(prefix="vredis"))
    server = RunningRedis(program, folder, _free_port())
    try:
        server.start()
        yield server
    finally:
        server.stop()
        shutil.rmtree(folder, ignore_errors=True)
