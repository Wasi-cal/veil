import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Self
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel


class SeenRequest(BaseModel):
    method: str
    path: str
    query: dict[str, list[str]]
    authorization: str | None
    body: dict | None


class StubGitHubServer:
    """A local HTTP server that answers like api.github.com. Routes map (method, path) to (status, JSON)."""

    def __init__(self):
        self.routes: dict[tuple[str, str], tuple] = {}
        self.seen: list[SeenRequest] = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def _answer(self):
                parts = urlsplit(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                server.seen.append(
                    SeenRequest(
                        method=self.command,
                        path=parts.path,
                        query=parse_qs(parts.query),
                        authorization=self.headers.get("Authorization"),
                        body=json.loads(raw) if raw else None,
                    )
                )
                status, payload, *extra = server.routes.get(
                    (self.command, parts.path), (404, {"message": "Not Found"})
                )
                data = json.dumps(payload).encode()
                self.send_response(status)
                for name, value in (extra[0] if extra else {}).items():
                    self.send_header(name, value)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = _answer

            def log_message(self, *_args):
                pass

        self._http = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._http.server_port}"
        self._thread = threading.Thread(target=self._http.serve_forever, daemon=True)

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._http.shutdown()
        self._http.server_close()


def pull_json(
    number: int = 1,
    head: str = "feature-x",
    base: str = "main",
    state: str = "open",
    merged: bool = False,
    head_repo: str = "acme/app",
    labels: tuple[str, ...] = (),
    draft: bool = False,
) -> dict:
    """The fields of a GitHub pull request that the adapter reads."""
    return {
        "number": number,
        "html_url": f"https://github.example.invalid/acme/app/pull/{number}",
        "state": state,
        "merged_at": "2026-01-01T00:00:00Z" if merged else None,
        "draft": draft,
        "title": "t",
        "body": "b",
        "head": {"ref": head, "repo": {"full_name": head_repo}},
        "base": {"ref": base, "repo": {"full_name": "acme/app"}},
        "labels": [{"name": name} for name in labels],
    }
