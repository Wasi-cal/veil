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


class StubHttpServer:
    """A local HTTP server that replays recorded responses.

    A route maps (method, path) to (status, JSON) or (status, JSON, headers).
    A list of such answers is played in order. The last answer repeats.
    """

    def __init__(self):
        self.routes: dict[tuple[str, str], tuple | list] = {}
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
                answer = server.routes.get(
                    (self.command, parts.path), (404, {"message": "Not Found"})
                )
                if isinstance(answer, list):
                    answer = answer.pop(0) if len(answer) > 1 else answer[0]
                status, payload, *extra = answer
                data = json.dumps(payload).encode()
                self.send_response(status)
                for name, value in (extra[0] if extra else {}).items():
                    self.send_header(name, value)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PUT = _answer

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
