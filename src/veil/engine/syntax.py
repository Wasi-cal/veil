import ast
import json
import tomllib
from collections.abc import Callable
from pathlib import PurePosixPath

from veil.engine.failed_fix import FailedFix

PARSERS: dict[str, Callable[[str], object]] = {
    ".py": ast.parse,
    ".json": json.loads,
    ".toml": tomllib.loads,
}


def check_parses(files: dict[str, str]) -> None:
    """Raise FailedFix for the first file that does not parse. Skip files of unknown type."""
    for path, content in files.items():
        parser = PARSERS.get(PurePosixPath(path).suffix.lower())
        if parser is None:
            continue
        try:
            parser(content)
        except (SyntaxError, ValueError, RecursionError) as error:
            raise FailedFix(f"The file {path} does not parse. {error}") from None
