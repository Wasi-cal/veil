# How veil works

This page explains what the code does, step by step. Read `GLOSSARY.md` for the terms.

## The short version

Veil takes open Gozu Tickets. Each ticket names one file and one line with a security finding. For each ticket, Veil asks an AI model to change the code. Then Veil opens a draft pull request. A human reviews the pull request.

The part that does this work is the Engine. You start it with one function call: `run(context)`.

## What you give to the Engine

The `context` holds four parts:

- **settings**: the limits, for example 25 steps and 200 changed lines.
- **tracker**: the place where the tickets are. In real use this is Jira.
- **repo provider**: gives a copy of the repository and opens pull requests. In real use this is GitHub.
- **model client**: talks to the AI model.

The Engine knows only the shape of these parts. It does not know Jira, GitHub or OpenAI. In the tests, fakes take their place. The real parts come in later tickets (GR-18 to GR-20). This is why the tests need no network.

## What happens in one run

The function `run` handles the tickets one by one. For each ticket it calls `attempt`. An attempt has these steps:

1. Open a copy of the repository.
2. Read the file that the ticket names. Refuse if the file may hold secrets.
3. Build the first message to the model. It holds the repository, file, line, severity and finding. It also holds about 40 lines of code around the flagged line. The Engine marks the text from the ticket as untrusted data.
4. Talk to the model. The model answers with tool calls. The Engine runs each call and sends the result back. This repeats until the model calls `finish`.
5. Check the change. It must not be empty. It must have 200 changed lines or fewer. Each edited file must still parse.
6. Publish. The Engine commits the change on a branch that starts with `gozu/fix-`. It opens a draft pull request. It adds a comment with the link on the ticket. It moves the ticket to In Review.

## When an attempt fails

An attempt can stop with a Failed Fix. This happens at the step cap, at a failed check, or when the ticket points at a file that the Engine cannot read. The Engine then does three things:

1. It adds a comment with the reason on the ticket.
2. It adds the label `veil-failed-fix`.
3. It keeps the ticket open.

The Engine then goes on with the next ticket. A Failed Fix is not an error. The run does not stop.

## The five tools

The model can call five tools:

| Tool | What it does |
|---|---|
| `read_file` | Returns up to 300 lines of a file. |
| `search` | Returns up to 50 matching lines. |
| `list_dir` | Lists the files in one folder. |
| `edit_file` | Replaces text in an existing file. |
| `finish` | Ends the conversation. The Engine then checks the change. |

A tool never raises an error. If a call is wrong, the tool returns text that starts with `Error:` or `Refused:`. The model can then try again. Each result has a limit of 8 KB.

## The safety rules

These rules are code. Settings cannot turn them off.

- The Engine never edits `.github/workflows/`, lockfiles or secret files.
- The Engine never creates or deletes a file.
- The Engine never reads `.env` files, keys or `.git/`.
- The Engine never touches a path outside the repository.
- The class `WorkingCopy` checks each edit before it writes the edit. A refused edit changes nothing.

## Where to find things

| You want to change | Open this folder |
|---|---|
| The order of the steps in an attempt | `fix/` |
| What a tool does | `tools/handlers/` |
| A rule about paths, the diff limit or the syntax check | `workspace/` |
| What the Engine needs from Jira, GitHub or the model | `interfaces/` |
| The shape of a ticket, a setting or the report | `models/` |
| A fixed value, such as a limit or a tool name | `constants/` |

A folder imports only from the folders below it. The file `run.py` is at the top. The folders `errors/` and `constants/` are at the bottom. A contract in `pyproject.toml` checks this.

## How the tests work

Almost every test calls `run(context)` with three fakes. The model fake plays a script of tool calls. The repo fake uses real local git repositories. The test then checks the result: pull requests, commits, ticket comments, labels and the report. The tests do not call the internal functions.

Example: the script says "edit one line, then finish". The test checks that one draft pull request exists and that the ticket is In Review.

## One example from start to end

Ticket GR-100 says: "Line 3 of `app.py` uses `eval(input())`."

1. `run` reads GR-100 from the tracker.
2. `attempt` opens the repository and reads `app.py`.
3. The model gets the first message. It calls `edit_file` and replaces `eval(input())` with `int(input())`.
4. The `WorkingCopy` checks the edit and writes it. The result is "Edit applied."
5. The model calls `finish`.
6. The Engine checks the change. One line changed. The file still parses.
7. The Engine commits, opens a draft pull request and comments on GR-100. GR-100 moves to In Review.

If the model calls `edit_file` on `.env`, the result is `Refused:` and nothing changes. The model can try another edit.
