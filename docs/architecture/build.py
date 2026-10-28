"""Build docs/architecture/index.html from the real code.

Run it from the repository root: python docs/architecture/build.py
The page reads the real imports of every file. Each file needs a description in DESCRIPTIONS.
"""

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent / "index.html"

DESCRIPTIONS = {
    "src/veil/engine/__init__.py": "The public door of the Engine. It exports run, Context and the main models.",
    "src/veil/engine/run.py": "The entry point, run(context). It loops over the tickets, skips the ones that have a fix, records each Failed Fix and stops at the token ceiling.",
    "src/veil/engine/eligibility/select.py": "Decides if the Engine may fix a ticket: the no-loop rule, the Failed Fix label, the issue label and the check for an existing Fix.",
    "src/veil/engine/context.py": "The Context: settings, tracker, repo provider and model client. The caller builds it.",
    "src/veil/engine/fix/attempt.py": "One attempt to fix one ticket with one model. It opens a new workspace, builds the working copy and runs the steps.",
    "src/veil/engine/fix/escalation.py": "Tries the cheap model. If the attempt fails, it tries the strong model once on a fresh checkout.",
    "src/veil/engine/fix/conversation.py": "The loop with the model. It runs the tool calls, enforces the step cap and checks the token ceiling.",
    "src/veil/engine/fix/prompt.py": "Builds the first message to the model: ticket facts and the code around the flagged line.",
    "src/veil/engine/fix/publish.py": "Commits the Fix, opens a draft Fix PR, comments on the ticket and sets In Review.",
    "src/veil/engine/fix/failures.py": "Records a Failed Fix: the reason comment, the marker label and the outcome. Also marks tickets as left for the next run.",
    "src/veil/engine/tools/toolbox.py": "Finds the tool by name, checks the arguments, runs the handler and cuts the result.",
    "src/veil/engine/tools/result_cap.py": "Cuts a tool result to 8 KB and adds the note that tells the model to narrow the request.",
    "src/veil/engine/tools/handlers/edit_file.py": "The edit_file tool. It asks the working copy to replace text in a file.",
    "src/veil/engine/tools/handlers/read_file.py": "The read_file tool. It returns up to 300 lines of a file, from a start line.",
    "src/veil/engine/tools/handlers/search.py": "The search tool. It returns up to 50 lines that match a regular expression.",
    "src/veil/engine/tools/handlers/list_dir.py": "The list_dir tool. It lists the files and folders in one folder.",
    "src/veil/engine/tools/handlers/readable.py": "Helpers for the read tools: which paths and which files the model may read.",
    "src/veil/engine/workspace/working_copy.py": "Applies edits to the workspace. It checks each edit before it writes and keeps the changed lines.",
    "src/veil/engine/workspace/path_rules.py": "The safety rules for paths: outside the repository, workflows, lockfiles and secret files.",
    "src/veil/engine/workspace/diff.py": "Counts the changed lines. Each changed line counts once.",
    "src/veil/engine/workspace/syntax.py": "Checks that edited .py, .json and .toml files still parse.",
    "src/veil/engine/interfaces/__init__.py": "Exports the four interfaces.",
    "src/veil/engine/interfaces/tracker.py": "Interface: list the open tickets, add a comment, set a status and add a label.",
    "src/veil/engine/interfaces/repo_provider.py": "Interface: open a workspace, find an existing Fix for an issue label and open a draft pull request with labels.",
    "src/veil/engine/interfaces/workspace.py": "Interface: read, list, write and commit files in one checkout of a repository.",
    "src/veil/engine/interfaces/model_client.py": "Interface: send the messages and the model name to the model and get the next tool calls.",
    "src/veil/engine/models/__init__.py": "Exports the five main models.",
    "src/veil/engine/models/ticket/ticket.py": "A Gozu Ticket: key, repository, file, line, severity, finding, branch and labels.",
    "src/veil/engine/models/provider/existing_fix.py": "A Fix that the repo provider already has for a ticket: an open PR or a fix branch.",
    "src/veil/engine/models/llm/tool_call.py": "One tool call from the model: a name and arguments.",
    "src/veil/engine/models/llm/model_reply.py": "One reply from the model: the tool calls and the tokens used.",
    "src/veil/engine/models/config/settings.py": "The settings: the two model names, the token ceiling and the limits. Each has a default and a bound. Unknown settings are not allowed.",
    "src/veil/engine/models/report/run_report.py": "The run report: the pull requests, the outcome of each ticket, the skipped tickets with their reasons and the tokens used.",
    "src/veil/engine/models/tool_args/edit_file_args.py": "The arguments of edit_file: path, old text and new text.",
    "src/veil/engine/models/tool_args/read_file_args.py": "The arguments of read_file: path and start line.",
    "src/veil/engine/models/tool_args/search_args.py": "The arguments of search: a regular expression.",
    "src/veil/engine/models/tool_args/list_dir_args.py": "The arguments of list_dir: a folder path.",
    "src/veil/engine/errors/failed_fix.py": "Error type: the Engine cannot fix a ticket within its limits. It carries the reason.",
    "src/veil/engine/errors/attempt_failed.py": "Error type: an attempt failed after the model started. A stronger model can try again. It is not a Failed Fix.",
    "src/veil/engine/errors/budget_exhausted.py": "Error type: the run used its token ceiling. The Engine stops and leaves the rest of the tickets for the next run.",
    "src/veil/engine/errors/edit_rejected.py": "Error type: an edit breaks a limit or a rule. The model gets the message.",
    "src/veil/engine/errors/rule_violation.py": "Error type: a path breaks a safety rule.",
    "src/veil/engine/constants/limits.py": "The default limits: 25 steps, 200 changed lines, 300 lines, 50 matches, 8 KB and 100,000 tokens.",
    "src/veil/engine/constants/models.py": "The default names of the cheap model and the strong model.",
    "src/veil/engine/constants/paths.py": "Protected folders, lockfile names and the patterns of secret files.",
    "src/veil/engine/constants/tools.py": "The names of the five tools.",
    "src/veil/engine/constants/outcomes.py": "The outcome words of the run report: fixed, failed, skipped and left for the next run.",
    "src/veil/engine/constants/branches.py": "The prefix of the branches that the Engine makes: gozu/fix-.",
    "src/veil/engine/constants/labels.py": "The label names: the issue label prefix and the Failed Fix marker.",
    "src/veil/engine/constants/skip_reasons.py": "The reasons to skip a ticket.",
    "src/veil/engine/fix/budget.py": "Checks the token ceiling before an attempt and before each model call.",
    "src/veil/engine/constants/statuses.py": "The ticket status that the Engine sets: In Review.",
    "src/veil/engine/constants/prompt.py": "Prompt values: 20 lines on each side of the flagged line and the names of the untrusted tags.",
    "tests/architecture/test_layers.py": "Checks the folder order, the rule for adapters and shells, and that the Engine reads no environment variables.",
    "tests/engine/flow/test_fix_flow.py": "The normal path: one commit, one draft PR, a ticket comment, In Review and the report.",
    "tests/engine/escalation/test_escalation.py": "A failed cheap attempt leads to one strong attempt. A failed strong attempt is a Failed Fix.",
    "tests/engine/budget/test_token_ceiling.py": "The token ceiling counts all attempts and leaves the rest of the tickets for the next run.",
    "tests/engine/limits/test_step_cap.py": "The step cap of 25 tool calls ends the attempt as a Failed Fix.",
    "tests/engine/limits/test_diff_limit.py": "The diff limit of 200 changed lines. Line endings and spaces count.",
    "tests/engine/limits/test_result_caps.py": "The caps on tool results: 300 lines, 50 matches and 8 KB.",
    "tests/engine/edits/test_edit_refusals.py": "Refused edits: workflows, lockfiles, secret files, outside paths, new files and deletions.",
    "tests/engine/edits/test_syntax_check.py": "A file that no longer parses fails the attempt at finish.",
    "tests/engine/reads/test_read_refusals.py": "Secret files are never read or searched. Settings add patterns but cannot remove them.",
    "tests/engine/reads/test_list_dir.py": "list_dir shows only the asked folder and hides secret files.",
    "tests/engine/eligibility/test_eligibility.py": "Skip rules, the report of skipped tickets and a second run that makes no duplicates.",
    "tests/engine/failures/test_failed_fix.py": "Each way to a Failed Fix. A Failed Fix does not stop the next ticket.",
    "tests/engine/failures/test_bad_tool_calls.py": "A bad tool call gives an error to the model. The run goes on.",
    "tests/engine/settings/test_defaults.py": "The default limits, the bounds of the settings and the safety rules that are not settings.",
    "tests/fakes/__init__.py": "Exports the fakes and the helpers that build tool calls.",
    "tests/fakes/tracker.py": "A fake tracker. It keeps the status, comments and labels of each ticket.",
    "tests/fakes/repo.py": "A fake repo provider on real local git repositories. No network.",
    "tests/fakes/model.py": "A fake model client. It plays one script, or one script for each model name.",
    "tests/support/scenario.py": "Builds a test run: the context, the fakes and common scripts.",
    "tests/support/tool_results.py": "Runs one attempt and returns what the model got back for each tool call.",
}

GROUP_NOTES = {
    "engine": "The public door. Callers import from here.",
    "run": "The top of the Engine. It starts one attempt for each ticket that the Engine may fix.",
    "eligibility": "The rules that decide which tickets the Engine may fix.",
    "fix": "One attempt to fix one ticket, step by step.",
    "tools": "The tools that the model can call. Each tool has its own file.",
    "context": "What the caller passes in.",
    "workspace": "Safe edits: the rules that stop a bad edit before the Engine writes it.",
    "interfaces": "What the Engine needs from the outside. Fakes and real parts both fit these shapes.",
    "models": "The pydantic models. One folder for each purpose.",
    "errors": "The error types.",
    "constants": "The fixed values.",
    "tests/architecture": "Tests of the structure.",
    "tests/engine/flow": "Tests of the normal path.",
    "tests/engine/limits": "Tests of the limits.",
    "tests/engine/escalation": "Tests of the second attempt with the strong model.",
    "tests/engine/budget": "Tests of the token ceiling.",
    "tests/engine/eligibility": "Tests of which tickets the Engine skips, and of the second run.",
    "tests/engine/edits": "Tests of edit rules and the syntax check.",
    "tests/engine/reads": "Tests of what the model may read.",
    "tests/engine/failures": "Tests of Failed Fixes and bad tool calls.",
    "tests/engine/settings": "Tests of the settings.",
    "tests/fakes": "The fake parts. They replace Jira, GitHub and the model.",
    "tests/support": "Helpers that build a test run.",
}

# From top to bottom. A folder imports only from the rows below it.
LAYERS = [
    ["run"],
    ["fix", "eligibility"],
    ["tools", "context"],
    ["workspace"],
    ["interfaces"],
    ["models"],
    ["errors", "constants"],
]
SRC_ORDER = [
    "engine",
    "run",
    "fix",
    "eligibility",
    "tools",
    "context",
    "workspace",
    "interfaces",
    "models",
    "errors",
    "constants",
]
TEST_ORDER = [
    "tests/engine/flow",
    "tests/engine/escalation",
    "tests/engine/budget",
    "tests/engine/eligibility",
    "tests/engine/limits",
    "tests/engine/edits",
    "tests/engine/reads",
    "tests/engine/failures",
    "tests/engine/settings",
    "tests/architecture",
    "tests/fakes",
    "tests/support",
]


def module_name(path: Path) -> str:
    parts = list(path.relative_to(ROOT).with_suffix("").parts)
    if parts[0] == "src":
        parts = parts[1:]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def group_of(rel: str) -> str:
    if rel.startswith("tests/"):
        return (
            "/".join(rel.split("/")[:-1])
            if rel.count("/") > 2
            or "/fakes/" in rel
            or "/support/" in rel
            or "/architecture/" in rel
            else "tests"
        )
    inner = rel.removeprefix("src/veil/engine/")
    if "/" in inner:
        return inner.split("/")[0]
    return {"__init__.py": "engine", "run.py": "run", "context.py": "context"}[inner]


def read_imports(path: Path, known: set[str]) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            targets = [f"{node.module}.{alias.name}" for alias in node.names] + [
                node.module
            ]
        else:
            continue
        for target in targets:
            while target and target not in known:
                target = target.rpartition(".")[0]
            if target:
                found.add(target)
                break
    return found


def collect() -> dict:
    files = [
        p
        for base in ("src", "tests")
        for p in sorted((ROOT / base).rglob("*.py"))
        if "__pycache__" not in p.parts
    ]
    files = [p for p in files if p.read_text().strip()]
    names = {module_name(p): p for p in files}
    missing = [
        str(p.relative_to(ROOT))
        for p in files
        if str(p.relative_to(ROOT)) not in DESCRIPTIONS
    ]
    if missing:
        sys.exit(f"Add a description in DESCRIPTIONS for: {missing}")
    nodes = {}
    for name, path in names.items():
        rel = str(path.relative_to(ROOT))
        imports = sorted(read_imports(path, set(names)) - {name})
        nodes[name] = {
            "id": name,
            "path": rel,
            "file": path.name,
            "group": group_of(rel),
            "desc": DESCRIPTIONS[rel],
            "lines": len([l for l in path.read_text().splitlines() if l.strip()]),
            "imports": imports,
            "importedBy": [],
        }
    for name, node in nodes.items():
        for target in node["imports"]:
            nodes[target]["importedBy"].append(name)
    empty = len(
        [
            p
            for base in ("src", "tests")
            for p in (ROOT / base).rglob("__init__.py")
            if not p.read_text().strip()
        ]
    )
    return {"nodes": list(nodes.values()), "emptyInits": empty}


def folder_edges(nodes: list[dict]) -> dict:
    by_id = {n["id"]: n for n in nodes}
    edges: dict[str, dict[str, int]] = {}
    for node in nodes:
        if node["path"].startswith("tests/"):
            continue
        for target in node["imports"]:
            a, b = node["group"], by_id[target]["group"]
            if a != b and b != "engine":
                edges.setdefault(a, {})[b] = edges.setdefault(a, {}).get(b, 0) + 1
    return edges


def upward_imports(edges: dict) -> list[str]:
    rank = {g: i for i, row in enumerate(LAYERS) for g in row}
    # The public door (engine/__init__.py) is above every folder, so its imports go down.
    return [
        f"{a} -> {b}"
        for a, targets in edges.items()
        if a != "engine"
        for b in targets
        if rank[b] < rank[a]
    ]


# ---------- the sequence diagram of one run, as SVG ----------
LIFELINES = [
    "run.py",
    "attempt.py",
    "RepoProvider",
    "WorkingCopy",
    "conversation.py",
    "ModelClient",
    "Toolbox + handlers",
    "Tracker",
]


def sequence_svg() -> str:
    width, gap, top = 1240, 150, 56
    xs = [70 + i * gap for i in range(len(LIFELINES))]
    steps = [
        (0, 7, "1  open_tickets()", False, "then skip tickets that have a fix"),
        (
            0,
            1,
            "2  fix_ticket -> attempt(ticket, model)",
            False,
            "cheap model first, then the strong model",
        ),
        (1, 2, "3  open_workspace(repo)", False, "a new Workspace for each attempt"),
        (1, 3, "4  WorkingCopy(workspace, settings)", False, "created here"),
        (1, 3, "5  read(ticket.file)", False, ""),
        (1, 4, "6  converse(...)", False, ""),
        (4, 5, "7  next(messages)", False, "tool calls"),
        (4, 6, "8  run(call)", False, "one result text"),
        (6, 3, "9  edit / read / list_files", False, ""),
        (1, 3, "10  verify()", False, "at finish"),
        (1, 2, "11  commit + draft PR", False, "publish.py"),
        (1, 7, "12  add_comment + set_status", False, "In Review"),
    ]
    row, y0 = 46, top + 30
    height = y0 + row * (len(steps) + 4) + 40
    out = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Sequence of one run" class="seq">',
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>',
    ]
    for x, name in zip(xs, LIFELINES):
        out.append(
            f'<rect x="{x - 66}" y="8" width="132" height="34" rx="8" class="head"/><text x="{x}" y="30" text-anchor="middle" class="headtext">{name}</text>'
        )
        out.append(f'<line x1="{x}" y1="42" x2="{x}" y2="{height - 20}" class="life"/>')
    y = y0
    for i, (a, b, label, _, note) in enumerate(steps):
        y += row
        if i == 6:
            out.append(
                f'<rect x="{xs[4] - 100}" y="{y - 52}" width="{xs[6] - xs[4] + 200}" height="{row * 3 + 28}" rx="8" class="loop"/><text x="{xs[4] - 92}" y="{y - 36}" class="looptext">repeat until finish or the step cap</text>'
            )
        x1, x2 = xs[a], xs[b]
        if a == b:
            continue
        out.append(
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" class="msg" marker-end="url(#arr)"/>'
        )
        mid = (x1 + x2) / 2
        out.append(
            f'<text x="{mid}" y="{y - 7}" text-anchor="middle" class="label">{label}</text>'
        )
        if note:
            out.append(
                f'<text x="{mid}" y="{y + 16}" text-anchor="middle" class="note">{note}</text>'
            )
    y += row + 18
    out.append(
        f'<rect x="20" y="{y}" width="{width - 40}" height="44" rx="8" class="fail"/>'
        f'<text x="36" y="{y + 27}" class="failtext">A failed cheap attempt leads to one strong attempt on a fresh checkout. If that fails too, run.py records a Failed Fix and goes on. At the token ceiling the run stops and leaves the rest.</text>'
    )
    out.append("</svg>")
    return "".join(out)


TEMPLATE = (
    (Path(__file__).resolve().parent / "template.html").read_text()
    if (Path(__file__).resolve().parent / "template.html").exists()
    else None
)


def main() -> None:
    data = collect()
    edges = folder_edges(data["nodes"])
    data.update(
        {
            "groupNotes": GROUP_NOTES,
            "layers": LAYERS,
            "srcOrder": SRC_ORDER,
            "testOrder": TEST_ORDER,
            "folderEdges": edges,
            "upward": upward_imports(edges),
        }
    )
    if TEMPLATE is None:
        sys.exit("Missing docs/architecture/template.html")
    payload = json.dumps(data).replace("</", "<\\/")
    OUTPUT.write_text(
        TEMPLATE.replace("__DATA__", payload).replace("__SEQUENCE__", sequence_svg())
    )
    print(
        f"Wrote {OUTPUT.relative_to(ROOT)}: {len(data['nodes'])} files, {len(data['upward'])} upward imports"
    )


if __name__ == "__main__":
    main()
