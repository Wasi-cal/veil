import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "src" / "veil" / "engine"
ENV_NAMES = {"environ", "getenv", "putenv"}


def test_engine_imports_nothing_from_adapters_or_shells():
    lint_imports = Path(sys.executable).parent / "lint-imports"

    result = subprocess.run(
        [str(lint_imports)], cwd=ROOT, capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stdout


def test_engine_reads_no_environment_variables():
    offenders = []
    for path in ENGINE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Attribute) and node.attr in ENV_NAMES:
                offenders.append(f"{path.name}:{node.lineno}")
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "os"
                and any(a.name in ENV_NAMES for a in node.names)
            ):
                offenders.append(f"{path.name}:{node.lineno}")

    assert offenders == []


# These hold imported functions or objects built from code, so a constants folder cannot hold them.
REGISTRIES = {"TOOLS", "PARSERS", "_OPENER"}


def constants_outside_the_constants_folders(allowed: set[str]) -> list[str]:
    offenders = []
    for path in (ROOT / "src").rglob("*.py"):
        if "constants" in path.parts:
            continue
        for node in ast.parse(path.read_text()).body:
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
                if isinstance(node, ast.AnnAssign)
                else []
            )
            for target in targets:
                name = getattr(target, "id", "")
                if name.isupper() and name not in allowed:
                    offenders.append(f"{path.name}:{name}")
    return offenders


def test_every_constant_lives_in_a_constants_folder():
    assert constants_outside_the_constants_folders(REGISTRIES) == []


def test_the_constants_check_finds_a_constant_in_the_wrong_place():
    found = constants_outside_the_constants_folders(set())

    assert set(found) == {
        "toolbox.py:TOOLS",
        "syntax.py:PARSERS",
        "http_api.py:_OPENER",
    }
