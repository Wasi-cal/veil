import ast

from veil.engine.constants.breaking import (
    PARAMETERS_REASON,
    POSITIONAL_KINDS,
    REMOVED_REASON,
)

# A parameter: its name, its kind and whether it has a default value.
_Param = tuple[str, str, bool]
# A public name of a file: its kind, its parameters and the class that owns it, if any.
_Entry = tuple[str, tuple[_Param, ...], str | None]


def interface_reasons(path: str, before: str, after: str) -> list[str]:
    """Say what a Python edit does to the public interface of the file. Return one reason for each change.

    A public function, class or method is one with no leading underscore. `__init__` counts as public, because it
    gives the parameters of its class. A name that is removed or renamed is a change. A parameter list that can
    break a caller is a change. A new parameter with a default after the old ones is not.
    A file that is not Python, or that does not parse, gives no reason.
    """
    if not path.endswith(".py"):
        return []
    old, new = _interface(before), _interface(after)
    if old is None or new is None:
        return []
    reasons = []
    for name, (kind, params, owner) in old.items():
        if owner is not None and owner not in new:
            continue  # The reason for the removed class covers its methods.
        found = new.get(name)
        if found is None or found[0] != kind:
            reasons.append(REMOVED_REASON.format(kind=kind, name=name, path=path))
        elif not _compatible(params, found[1]):
            reasons.append(PARAMETERS_REASON.format(kind=kind, name=name, path=path))
    return reasons


def _interface(text: str) -> dict[str, _Entry] | None:
    try:
        tree = ast.parse(text)
    except (
        SyntaxError,
        ValueError,
        RecursionError,
        MemoryError,
    ):  # A deep nest must not stop the run.
        return None
    entries: dict[str, _Entry] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if _public(node.name):
                entries[node.name] = ("function", _params(node.args), None)
        elif isinstance(node, ast.ClassDef) and _public(node.name):
            entries[node.name] = ("class", (), None)
            for member in node.body:
                if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef) and (
                    _public(member.name) or member.name == "__init__"
                ):
                    qualified = f"{node.name}.{member.name}"
                    entries[qualified] = ("method", _params(member.args), node.name)
    return entries


def _public(name: str) -> bool:
    return not name.startswith("_")


def _params(args: ast.arguments) -> tuple[_Param, ...]:
    positional = [*args.posonlyargs, *args.args]
    first_default = len(positional) - len(args.defaults)
    params: list[_Param] = [
        (
            arg.arg,
            "posonly" if index < len(args.posonlyargs) else "pos",
            index >= first_default,
        )
        for index, arg in enumerate(positional)
    ]
    if args.vararg:
        params.append((args.vararg.arg, "var", True))
    params += [
        (arg.arg, "kwonly", default is not None)
        for arg, default in zip(args.kwonlyargs, args.kw_defaults)
    ]
    if args.kwarg:
        params.append((args.kwarg.arg, "varkw", True))
    return tuple(params)


def _compatible(old: tuple[_Param, ...], new: tuple[_Param, ...]) -> bool:
    """Check that every call that worked with the old parameters works with the new ones."""
    old_positional = [p for p in old if p[1] in POSITIONAL_KINDS]
    new_positional = [p for p in new if p[1] in POSITIONAL_KINDS]
    kept = new_positional[: len(old_positional)]
    if [p[:2] for p in kept] != [p[:2] for p in old_positional]:
        return False
    if any(was[2] and not now[2] for was, now in zip(old_positional, kept)):
        return False
    if any(not p[2] for p in new_positional[len(old_positional) :]):
        return False
    old_keyword = {p[0]: p for p in old if p[1] == "kwonly"}
    new_keyword = {p[0]: p for p in new if p[1] == "kwonly"}
    for name, was in old_keyword.items():
        now = new_keyword.get(name)
        if now is None or (was[2] and not now[2]):
            return False
    if any(name not in old_keyword and not p[2] for name, p in new_keyword.items()):
        return False
    return all(
        any(p[1] == kind for p in new)
        for kind in ("var", "varkw")
        if any(p[1] == kind for p in old)
    )
