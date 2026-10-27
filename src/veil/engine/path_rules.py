"""Safety rules about paths. They are code, not settings."""

import posixpath
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from veil.engine.constants.paths import (
    LOCKFILE_NAMES,
    PROTECTED_DIRS,
    READ_REFUSED_DIRS,
    READ_REFUSED_PATTERNS,
)


class RuleViolation(Exception):
    """A path rule was broken. `str(error)` says which."""


def normalize_dir(path: str) -> str:
    """A folder inside the repo. The repo root is the empty string."""
    clean = PurePosixPath(posixpath.normpath(path.replace("\\", "/")))
    if clean.is_absolute() or clean.parts[:1] == ("..",):
        raise RuleViolation("the path is outside the repository.")
    return "" if clean.parts == () else clean.as_posix()


def normalize_file(path: str) -> str:
    """A file inside the repo."""
    clean = normalize_dir(path)
    if not clean:
        raise RuleViolation("the path must name a file inside the repository.")
    return clean


def check_readable(path: str, extra_patterns: tuple[str, ...] = ()) -> str:
    path = normalize_file(path)
    lowered = path.lower()
    parts = PurePosixPath(lowered).parts
    patterns = [pattern.lower() for pattern in READ_REFUSED_PATTERNS + extra_patterns]
    if any(part in READ_REFUSED_DIRS for part in parts) or any(
        fnmatchcase(parts[-1], pattern) or fnmatchcase(lowered, pattern)
        for pattern in patterns
    ):
        raise RuleViolation("this file may hold secrets.")
    return path


def check_editable(path: str, extra_patterns: tuple[str, ...] = ()) -> str:
    path = check_readable(path, extra_patterns)
    lowered = path.lower()
    if any(lowered.startswith(f"{protected}/") for protected in PROTECTED_DIRS):
        raise RuleViolation("this path is protected.")
    if PurePosixPath(lowered).name in LOCKFILE_NAMES:
        raise RuleViolation("lockfiles are protected.")
    return path
