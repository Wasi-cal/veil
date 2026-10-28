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
    "src/veil/engine/__init__.py": "The public door of the Engine. It exports run, Context, the main models and the four interfaces.",
    "src/veil/engine/run.py": "The entry point, run(context). It skips tickets that have a fix, makes groups, fixes each group and stops at the token ceiling.",
    "src/veil/engine/eligibility/select.py": "Decides if the Engine may fix a ticket. The rules are the no-loop rule, the Failed Fix label, the issue label, the open Source PR and an existing Fix.",
    "src/veil/engine/context.py": "The Context: settings, tracker, repo provider, model client and the credential values. The caller builds it.",
    "src/veil/engine/fix/group.py": "Fixes the tickets of one group in one checkout. It commits each Fix, leaves out Failed Fixes and opens one PR.",
    "src/veil/engine/fix/finish.py": "Checks the finish call of the model: one-line commit message, and an explanation of at most 3 sentences.",
    "src/veil/engine/grouping/plan.py": "Puts tickets into groups. Low and Medium tickets share a Shared PR. Each High ticket gets a High PR. High tickets of one file share one PR.",
    "src/veil/engine/grouping/severity.py": "Gives the Severity Bucket of a severity word from the severity map. An unknown word is High.",
    "src/veil/engine/constants/severity.py": "The three Severity Buckets and the default severity map.",
    "src/veil/engine/models/fix/fix.py": "A Fix that passed: the ticket, the commit message and the explanation.",
    "src/veil/engine/models/group/fix_group.py": "The tickets that go into one Fix PR, with their repository, Source PR branch and the reason for the group. It gives the branch name and the title of the PR.",
    "src/veil/engine/models/group/group_plan.py": "The groups for this run and the tickets that wait for a later run.",
    "src/veil/engine/models/tool_args/finish_args.py": "The arguments of finish: a one-line commit message and an explanation.",
    "src/veil/engine/fix/secret_check.py": "Fails the attempt if a Fix adds a secret to a file, or if the commit message or the explanation holds one.",
    "src/veil/engine/secrets/scan.py": "Finds a secret in a text: a credential value of this run or a known secret pattern. It can find only the secrets that a new text adds to an old text.",
    "src/veil/engine/secrets/redact.py": "Replaces each credential value and each known secret pattern in a text with [redacted].",
    "src/veil/engine/constants/secrets.py": "The known secret patterns, the [redacted] marker and the name of the credential kind.",
    "src/veil/engine/fix/attempt.py": "One attempt to fix one ticket with one model, in the workspace of the group. It returns the Fix.",
    "src/veil/engine/fix/escalation.py": "Tries the cheap model. If the attempt fails, it discards the edits and tries the strong model once.",
    "src/veil/engine/fix/conversation.py": "The loop with the model. It runs the tool calls, enforces the step cap and checks the token ceiling.",
    "src/veil/engine/fix/prompt.py": "Builds the system message and the first message to the model. Text from tickets and files cannot end its untrusted block.",
    "src/veil/engine/fix/publish.py": "Opens one draft Fix PR for a group. It comments on each ticket and sets In Review.",
    "src/veil/engine/fix/failures.py": "Records a Failed Fix: the marker label first, then the reason comment, and the outcome.",
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
    "src/veil/engine/interfaces/tracker.py": "Interface: list the candidate tickets, add a comment, set a status and add a label.",
    "src/veil/engine/interfaces/repo_provider.py": "Interface: open a workspace on a branch, ask if a branch has an open PR, find an existing Fix for a query and open a draft pull request.",
    "src/veil/engine/interfaces/workspace.py": "Interface: read, list, write, commit and discard changes in one checkout of a repository.",
    "src/veil/engine/interfaces/model_client.py": "Interface: send the messages, the model name and the tools to the model. Get the next tool calls and the tokens used.",
    "src/veil/engine/models/__init__.py": "Exports the main models.",
    "src/veil/engine/models/ticket/ticket.py": "A Gozu Ticket: key, repository, file, line, severity, finding, branch and labels.",
    "src/veil/engine/models/provider/fix_query.py": "The question for the repo provider: is there a Fix for this ticket? It holds the repository, the issue label, the Source PR branch and the branch prefix.",
    "src/veil/engine/models/llm/tool_definition.py": "A tool that the model can call: a name, a description and a JSON schema of the arguments.",
    "src/veil/engine/tools/definitions.py": "Builds the tool definitions for the model from the argument models and the finish arguments.",
    "src/veil/engine/fix/pr_text.py": "The text of the PR body and of the comment on a ticket.",
    "src/veil/engine/fix/left_over.py": "Marks tickets as left for the next run. It does not touch them in the tracker.",
    "tests/engine/flow/test_model_contract.py": "The model gets the tools and a system message. Each tool result answers a call of the model.",
    "src/veil/engine/models/llm/tool_call.py": "One tool call from the model: a name, arguments and the id that the answer must name.",
    "src/veil/engine/models/llm/model_reply.py": "One reply from the model: the tool calls and the tokens used.",
    "src/veil/engine/models/config/settings.py": "The settings: the two model names, the token ceiling, the cap of the Shared PR, the branch prefix, the severity map, the limits and extra refused read patterns. Each has a default and a bound. Unknown settings are not allowed.",
    "src/veil/engine/models/report/run_report.py": "The run report: the pull requests, the outcome of each ticket, the skipped tickets with their reasons and the tokens used.",
    "src/veil/engine/models/tool_args/edit_file_args.py": "The arguments of edit_file: path, old text and new text.",
    "src/veil/engine/models/tool_args/read_file_args.py": "The arguments of read_file: path and start line.",
    "src/veil/engine/models/tool_args/search_args.py": "The arguments of search: a regular expression.",
    "src/veil/engine/models/tool_args/list_dir_args.py": "The arguments of list_dir: a folder path.",
    "src/veil/engine/errors/failed_fix.py": "Error type: the Engine cannot fix a ticket within its limits. It carries the reason.",
    "src/veil/engine/errors/attempt_failed.py": "Error type: an attempt failed after the model started. A stronger model can try again. It is not a Failed Fix.",
    "src/veil/engine/errors/budget_exhausted.py": "Error type: the run used its token ceiling. The Engine stops and leaves the rest of the tickets for the next run.",
    "src/veil/engine/errors/edit_rejected.py": "Error type: an edit breaks a limit or a rule. The model gets the message.",
    "src/veil/adapters/github/api.py": "The GitHubApi interface: find PRs and open a draft PR.",
    "src/veil/adapters/github/git_command.py": "Runs git with a small environment. Passes the token in a per-command header. Hides it in errors.",
    "src/veil/adapters/github/http_api.py": "The GitHub REST API over HTTP. The token goes in the Authorization header only.",
    "src/veil/adapters/github/models/pull_request.py": "A PR as the GitHub API shows it, with its state and head repository.",
    "src/veil/adapters/github/provider.py": "The real repo provider. Makes private checkouts, finds Fixes, pushes the Fix branch, opens draft PRs.",
    "src/veil/adapters/github/workspace.py": "One private git checkout. Edits, commits, discards changes and pushes the Fix branch.",
    "src/veil/engine/errors/repo_provider_error.py": "Error type: the repo provider could not do its task. The message has no credential value.",
    "tests/adapters/github/support.py": "Helpers: a local bare git remote and a provider that uses it.",
    "tests/adapters/github/test_checkout.py": "Checkout tests: shallow, private, no token on disk, cleanup, option-like names.",
    "tests/adapters/github/test_draft_pr.py": "Draft PR tests: push only the Fix branch, never a second PR.",
    "tests/adapters/github/test_existing_fix.py": "Tests for the Source PR check and the search for an existing Fix.",
    "tests/adapters/github/test_git_environment.py": "Tests that git gets the proxy and certificate variables and no other variable.",
    "tests/adapters/github/test_http_api.py": "Tests of the HTTP adapter against a local stub server.",
    "tests/fakes/github_api.py": "A GitHubApi that keeps its PRs in a list.",
    "src/veil/engine/errors/rule_violation.py": "Error type: a path breaks a safety rule.",
    "src/veil/engine/constants/limits.py": "The default limits and the bounds of the settings.",
    "src/veil/engine/constants/model_names.py": "The default names of the cheap model and the strong model.",
    "src/veil/engine/constants/paths.py": "Protected folders, lockfile names and the patterns of secret files.",
    "src/veil/engine/constants/tools.py": "The names of the five tools and their descriptions.",
    "src/veil/engine/constants/outcomes.py": "The outcome words of the run report: fixed, failed, skipped and left for the next run.",
    "src/veil/engine/constants/branches.py": "The prefix of the branches that the Engine makes: gozu/fix-.",
    "src/veil/engine/constants/labels.py": "The label names: the issue label prefix and the Failed Fix marker.",
    "src/veil/engine/constants/skip_reasons.py": "The reasons to skip a ticket.",
    "src/veil/engine/models/provider/draft_pr.py": "What the repo provider needs to open a draft Fix PR. The base is the branch of the Source PR.",
    "src/veil/engine/fix/budget.py": "Checks the token ceiling before an attempt and before each model call.",
    "src/veil/engine/constants/explanation.py": "How to count the sentences of an explanation: the end marks and the abbreviations.",
    "src/veil/engine/constants/fix_kinds.py": "The kinds of Fix that the repo provider can find: an open PR or a Fix branch.",
    "src/veil/engine/constants/group_kinds.py": "The two kinds of group: shared and high.",
    "src/veil/engine/constants/tool_messages.py": "The note that tells the model to narrow a request.",
    "src/veil/adapters/github/constants/git.py": "Git values: the GitHub URL, the token user, the ref prefix, the author and the network variables.",
    "src/veil/adapters/github/constants/http.py": "API values: the base URL, the version, the page size, the time-out and the error length.",
    "src/veil/adapters/github/constants/modes.py": "The mode of a private directory.",
    "src/veil/adapters/github/constants/pr_states.py": "The three states of a PR: open, closed and merged.",
    "src/veil/adapters/github/constants/repo_name.py": "The pattern of a safe repository name.",
    "src/veil/adapters/jira/adf.py": "Reads the text and the Details lines of a Jira description. Builds the body of a comment.",
    "src/veil/adapters/jira/constants/details.py": "The names of the Details lines that Gozurion writes and the names of its custom fields.",
    "src/veil/adapters/jira/constants/http.py": "Jira API values: the paths, the page size, the time-out and the gateway URL.",
    "src/veil/adapters/jira/constants/patterns.py": "The patterns of a safe ticket key, project key and label.",
    "src/veil/adapters/jira/constants/workflow.py": "The done category that the adapter never enters and the key of the comment property.",
    "src/veil/adapters/jira/gateway.py": "Finds the gateway URL of a Jira Cloud site from its cloud ID. A Shell calls it once.",
    "src/veil/adapters/jira/http_client.py": "Calls the Jira REST API with JSON. Sends the credentials in one header and hides them in errors.",
    "src/veil/adapters/jira/issue_parser.py": "Makes a Ticket from a Jira issue. Gives nothing for an issue that is not a finding of one line.",
    "src/veil/adapters/jira/models/jira_credentials.py": "The email and the token that a Shell passes in. They never show in repr.",
    "src/veil/adapters/jira/models/jira_settings.py": "The site, the project keys, the eligible label and the status names. No secret.",
    "src/veil/adapters/jira/tracker.py": "The real tracker for Jira. Finds eligible tickets, adds labels and comments, moves a ticket to a status.",
    "src/veil/adapters/no_redirect.py": "Opens a URL and never follows a redirect, so a token cannot reach another host.",
    "src/veil/engine/errors/tracker_error.py": "Error type: the tracker could not do its task. The message has no credential value.",
    "tests/adapters/jira/support.py": "Helper: a Jira tracker that talks to the stub server.",
    "tests/adapters/jira/test_changes.py": "Label and status tests: a repeat gives the same state, and a ticket is never closed.",
    "tests/adapters/jira/test_comments.py": "Comment tests: a hidden marker stops a repeat of the same comment.",
    "tests/adapters/jira/test_connection.py": "Tests of the credentials, the https rule, the errors, the redirects and the shape of the answers.",
    "tests/adapters/jira/test_open_tickets.py": "Tests of the search, the paging, the custom fields and the ticket that the adapter builds.",
    "tests/fakes/http_server.py": "A local HTTP server that replays recorded answers. It serves both adapter tests.",
    "tests/fakes/jira_fixtures.py": "Jira Cloud response shapes that follow the tickets that Gozurion writes.",
    "src/veil/adapters/constants/http.py": "API values that both adapters share: the time-out and the length of an error body.",
    "src/veil/adapters/json_http.py": "Calls a JSON API for both adapters. Hides the credentials in every error and follows no redirect.",
    "tests/adapters/jira/test_gateway.py": "Tests that find the gateway URL from the cloud ID of a site.",
    "tests/adapters/jira/test_settings.py": "Tests that the settings refuse a project key or a label that could change the search.",
    "tests/fakes/github_fixtures.py": "Pull request answers in the shape of the GitHub API.",
    "src/veil/engine/constants/statuses.py": "The ticket status that the Engine sets: In Review.",
    "src/veil/engine/constants/prompt.py": "Prompt values: the system message, 20 lines on each side of the flagged line and the untrusted tags.",
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
    "tests/engine/source_pr/test_source_pr.py": "The Engine builds the Fix on the Source PR branch. The Fix PR targets that branch. The Engine skips a ticket that has no open Source PR.",
    "tests/engine/grouping/test_shared_pr.py": "One Shared PR with a commit for each Fix, Failed Fixes left out, the cap, the token ceiling and a second run.",
    "tests/engine/grouping/test_high_pr.py": "A High PR for each High ticket, and one PR for High tickets of the same file with the reason in the body.",
    "tests/engine/grouping/test_grouping_settings.py": "The severity map and the branch prefix are settings.",
    "tests/engine/flow/test_fix_output.py": "The commit message and the explanation of the model go in the commit, the PR body and the ticket comment.",
    "tests/engine/secrets/test_secret_scan.py": "A secret in an added line, the commit message or the explanation fails the attempt. The redaction hides credential values.",
    "tests/engine/secrets/test_secret_guard.py": "The Context hides the credential values, refuses short ones and the Engine exports redact.",
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
    "tests/adapters/jira": "Tests of the real tracker for Jira against a stub HTTP server.",
    "adapters": "The real parts that fit the interfaces of the Engine. The Engine never imports them.",
    "tests/adapters/github": "Tests of the real repo provider against a local git remote and a stub GitHub server.",
    "engine": "The public door. Callers import from here.",
    "run": "The top of the Engine. It fixes the groups of tickets that the Engine may fix.",
    "eligibility": "The rules that decide which tickets the Engine may fix.",
    "grouping": "The rules that decide which tickets share one Fix PR.",
    "fix": "The fix of one group of tickets, step by step.",
    "tools": "The tools that the model can call. Each tool has its own file.",
    "context": "What the caller passes in.",
    "secrets": "Finds secrets in a text and hides the credential values of this run.",
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
    "tests/engine/secrets": "Tests of the secret scan and the redaction.",
    "tests/engine/grouping": "Tests of the Shared PR and the High PR.",
    "tests/engine/eligibility": "Tests of which tickets the Engine skips, and of the second run.",
    "tests/engine/source_pr": "Tests of the work on the branch of the Source PR.",
    "tests/engine/edits": "Tests of edit rules and the syntax check.",
    "tests/engine/reads": "Tests of what the model may read.",
    "tests/engine/failures": "Tests of Failed Fixes and bad tool calls.",
    "tests/engine/settings": "Tests of the settings.",
    "tests/fakes": "The fake parts. They replace Jira, GitHub and the model.",
    "tests/support": "Helpers that build a test run.",
}

# From top to bottom. A folder imports only from the rows below it.
LAYERS = [
    ["adapters"],
    ["run"],
    ["fix", "eligibility", "grouping"],
    ["tools", "context"],
    ["workspace", "secrets"],
    ["interfaces"],
    ["models"],
    ["errors", "constants"],
]
SRC_ORDER = [
    "adapters",
    "engine",
    "run",
    "fix",
    "eligibility",
    "grouping",
    "tools",
    "context",
    "workspace",
    "secrets",
    "interfaces",
    "models",
    "errors",
    "constants",
]
TEST_ORDER = [
    "tests/adapters/github",
    "tests/adapters/jira",
    "tests/engine/flow",
    "tests/engine/escalation",
    "tests/engine/budget",
    "tests/engine/secrets",
    "tests/engine/grouping",
    "tests/engine/eligibility",
    "tests/engine/source_pr",
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
    if rel.startswith("src/veil/adapters/"):
        return "adapters"
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
            "2  fix_group -> fix_ticket",
            False,
            "one group at a time, cheap model first",
        ),
        (
            1,
            2,
            "3  open_workspace(repo, branch)",
            False,
            "one Workspace for each group",
        ),
        (1, 3, "4  WorkingCopy(workspace, settings)", False, "created here"),
        (1, 3, "5  read(ticket.file)", False, ""),
        (1, 4, "6  converse(...)", False, ""),
        (4, 5, "7  next(messages, model, tools)", False, "tool calls"),
        (4, 6, "8  run(call)", False, "one result text"),
        (6, 3, "9  edit / read / list_files", False, ""),
        (1, 3, "10  verify()", False, "at finish"),
        (
            1,
            2,
            "11  open_draft_pr(draft)",
            False,
            "publish.py, after one commit for each Fix",
        ),
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
        f'<text x="36" y="{y + 27}" class="failtext">A failed cheap attempt leads to one strong attempt on a fresh checkout. If that fails too, group.py records a Failed Fix and goes on. At the token ceiling the run stops and leaves the rest.</text>'
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
