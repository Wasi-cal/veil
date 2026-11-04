import json
import re
import tomllib
from pathlib import PurePosixPath

from veil.engine.constants.breaking import (
    DEPENDENCY_REMOVED_REASON,
    MAJOR_REASON,
    MANIFEST_NAMES,
    NPM_DEPENDENCY_KEYS,
    REQUIREMENT_NAME,
    RUNTIME_REASON,
    VERSION_NUMBER,
)

# A manifest gives the dependencies (name -> version text) and the runtime
# requirements (name -> version text) that it states.
_Parsed = tuple[dict[str, str], dict[str, str]]


def manifest_reasons(path: str, before: str, after: str) -> list[str]:
    """Return a reason for each risky change between two texts of one manifest."""
    name = PurePosixPath(path).name
    if name not in MANIFEST_NAMES:
        return []
    old, new = _parse(name, before), _parse(name, after)
    if old is None or new is None:
        return []
    (old_deps, old_runtime), (new_deps, new_runtime) = old, new
    reasons = []
    for dep, spec in old_deps.items():
        if dep not in new_deps:
            reasons.append(DEPENDENCY_REMOVED_REASON.format(name=dep, path=path))
        elif _major_changed(spec, new_deps[dep]):
            reasons.append(
                MAJOR_REASON.format(name=dep, path=path, old=spec, new=new_deps[dep])
            )
    for runtime, spec in old_runtime.items():
        if runtime in new_runtime and _raised(spec, new_runtime[runtime]):
            reasons.append(
                RUNTIME_REASON.format(
                    name=runtime, path=path, old=spec, new=new_runtime[runtime]
                )
            )
    return reasons


def _parse(name: str, text: str) -> _Parsed | None:
    try:
        if name == "package.json":
            return _parse_package(json.loads(text))
        if name == "pyproject.toml":
            return _parse_pyproject(tomllib.loads(text))
    except ValueError:
        return None
    return _parse_requirements(text)


def _parse_package(data: object) -> _Parsed:
    data = _mapping(data)
    deps: dict[str, str] = {}
    for key in NPM_DEPENDENCY_KEYS:
        deps.update(_texts(_mapping(data.get(key))))
    return deps, _texts(_mapping(data.get("engines")))


def _parse_pyproject(data: dict) -> _Parsed:
    project = _mapping(data.get("project"))
    lines = _lines(project.get("dependencies"))
    for group in _mapping(project.get("optional-dependencies")).values():
        lines += _lines(group)
    for group in _mapping(data.get("dependency-groups")).values():
        lines += _lines(group)
    runtime = project.get("requires-python")
    return _requirements(lines), (
        {"requires-python": runtime} if isinstance(runtime, str) else {}
    )


def _parse_requirements(text: str) -> _Parsed:
    lines = [line.split(" #")[0].strip() for line in text.splitlines()]
    return _requirements([line for line in lines if line and line[0] not in "#-"]), {}


def _requirements(lines: list[str]) -> dict[str, str]:
    found = {}
    for line in lines:
        match = REQUIREMENT_NAME.match(line)
        if match:
            rest = re.sub(r"\[[^\]]*\]", "", line[match.end() :])
            spec = rest.split(";")[0].split("@")[0].replace(" ", "")
            found[match.group().lower().replace("_", "-")] = spec
    return found


def _mapping(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _texts(mapping: dict) -> dict[str, str]:
    return {k: v for k, v in mapping.items() if isinstance(v, str)}


def _lines(value: object) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _version(spec: str) -> tuple[int, ...] | None:
    match = VERSION_NUMBER.search(spec)
    return tuple(int(n) for n in match.group().split(".")) if match else None


def _major_changed(old: str, new: str) -> bool:
    before, after = _version(old), _version(new)
    if before is None or after is None:
        return False
    if before[0] != after[0]:
        return True
    return before[0] == 0 and _padded(before, 2) != _padded(after, 2)


def _raised(old: str, new: str) -> bool:
    before, after = _version(old), _version(new)
    if before is None or after is None:
        return False
    size = max(len(before), len(after))
    return _padded(after, size) > _padded(before, size)


def _padded(version: tuple[int, ...], size: int) -> tuple[int, ...]:
    return (version + (0,) * size)[:size]
