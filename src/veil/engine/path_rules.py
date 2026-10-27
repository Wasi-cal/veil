"""Safety rules for paths. These rules are code. They are not settings."""

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
    """The path breaks a rule. The message of the error names the rule."""


def normalize_dir(path: str) -> str:
    """A folder in the repository. The repository root is the empty string."""
    clean = PurePosixPath(posixpath.normpath(path.replace("\\", "/")))
    if clean.is_absolute() or clean.parts[:1] == ("..",):
        raise RuleViolation("The path is outside the repository.")
    return "" if clean.parts == () else clean.as_posix()


def normalize_file(path: str) -> str:
    """A file in the repository."""
    clean = normalize_dir(path)
    if not clean:
        raise RuleViolation("The path must name a file in the repository.")
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
        raise RuleViolation("This file may hold secrets.")
    return path


def check_editable(path: str, extra_patterns: tuple[str, ...] = ()) -> str:
    path = check_readable(path, extra_patterns)
    lowered = path.lower()
    if any(lowered.startswith(f"{protected}/") for protected in PROTECTED_DIRS):
        raise RuleViolation("The Engine protects this path.")
    if PurePosixPath(lowered).name in LOCKFILE_NAMES:
        raise RuleViolation("The Engine protects lockfiles.")
    return path
