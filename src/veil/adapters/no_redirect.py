import urllib.request
from typing import Any


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect. A redirect could send the credentials to another host."""

    def redirect_request(self, *_args, **_kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def open_without_redirect(request: urllib.request.Request, timeout: float) -> Any:
    """Open a request like `urlopen`. A redirect answer raises HTTPError and goes nowhere."""
    return _OPENER.open(request, timeout=timeout)
