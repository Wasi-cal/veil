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
