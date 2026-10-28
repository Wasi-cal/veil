# How veil works

This page explains what the code does, step by step. Read `GLOSSARY.md` for the terms.

## The short version

Veil takes open Gozu Tickets. Gozu makes a ticket when a developer raises a pull request and a scan finds a problem. We call that pull request the Source PR. Each ticket names one file and one line with a security finding. For each ticket, Veil asks an AI model to change the code. Then Veil opens a draft pull request. A human reviews the pull request.

The part that does this work is the Engine. You start it with one function call: `run(context)`.

## What you give to the Engine

The `context` holds four parts:

- **settings**: the limits, for example 25 steps and 200 changed lines.
- **tracker**: the place where the tickets are. In real use this is Jira.
- **repo provider**: gives a copy of the repository and opens pull requests. In real use this is GitHub.
- **model client**: talks to the AI model.

The Engine knows only the shape of these parts. It does not know Jira, GitHub or OpenAI. In the tests, fakes take their place. The real parts come in later tickets (GR-18 to GR-20). This is why the tests need no network.

## What happens in one run

The function `run` handles the tickets one by one. Before each ticket, it checks if the Engine may fix the ticket (see the section "Which tickets the Engine skips"). Then it calls `fix_ticket`. That function starts an attempt with the cheap model. If the attempt fails, it starts one more attempt with the strong model. An attempt has these steps:

1. Open a copy of the repository. This is the branch of the ticket, the branch of the Source PR.
2. Read the file that the ticket names. Refuse if the file may hold secrets.
3. Build the first message to the model. It holds the repository, file, line, severity and finding. It also holds about 40 lines of code around the flagged line. The Engine marks the text from the ticket as untrusted data.
4. Talk to the model. The model answers with tool calls. The Engine runs each call and sends the result back. This repeats until the model calls `finish`. Before each model call, the Engine checks the token ceiling.
5. Check the change. It must not be empty. It must have 200 changed lines or fewer. Each edited file must still parse.
6. Publish. The Engine commits the change on a branch that starts with `gozu/fix-`. It opens a draft pull request that targets the branch of the Source PR. It adds a comment with the link on the ticket. It moves the ticket to In Review.

## Which tickets the Engine skips

The tracker gives the Engine the candidates: tickets that are open, unassigned and marked by Gozu. The Engine then checks each candidate just before its attempt. The Engine skips a ticket for one of these reasons:

| Reason in the report | What it means |
|---|---|
| `raised_against_fix_branch` | The finding is on a `gozu/fix-*` branch. A human decides what happens to it. |
| `failed_fix` | The ticket has the label `veil-failed-fix`. It stays untouched until a human deletes the label. |
| `no_issue_label` | The ticket has no label that starts with `issue-`. The Engine cannot prove that no PR exists. |
| `source_pr_not_open` | The branch of the ticket has no open PR. The developer merged or closed the Source PR, or the branch never had a PR. |
| `open_pr` | The repo provider has an open PR that carries the issue label of the ticket. |
| `fix_branch` | The repo provider has a `gozu/fix-*` branch that carries the issue label. No PR is open. |

A skipped ticket opens no checkout, uses no tokens and gets no comment. The run report lists each skipped ticket under its reason.

This makes a second run safe. The Engine puts the issue label on each draft PR that it opens. The next run finds the PR and skips the ticket. The Engine skips a Failed Fix ticket too, so it gets no second comment. After a run that stopped at the token ceiling, the next run fixes only the tickets that the earlier run left.

If the tracker lists a ticket twice, the Engine uses it once. If two tickets have the same issue label, the Engine fixes the first one. It skips the second because the first PR already exists.

## When an attempt fails

An attempt fails at the step cap, when the model calls `finish` and made no change, or when an edited file does not parse. Then the Engine starts one more attempt with the strong model. This second attempt has these rules:

- It starts on a new checkout of the repository. It does not keep any edit of the first attempt.
- It gets only the reason of the failure, in its first message. It does not get the other messages of the first attempt.
- It is the last attempt. There is no third attempt.

A ticket file that the Engine cannot read does not start a second attempt. The model never ran, so the strong model cannot do better.

## Failed Fix

A Failed Fix happens when the second attempt fails too. The Engine then does three things:

1. It adds a comment on the ticket with the reason of each attempt.
2. It adds the label `veil-failed-fix`.
3. It keeps the ticket open.

The Engine then goes on with the next ticket. A Failed Fix is not an error. The run does not stop.

## The token ceiling

The run counts the tokens that the model API reports. It counts all attempts of all tickets together. The default ceiling is 100,000 tokens.

Before each model call, the Engine checks the count. If the count is at the ceiling, the run stops. This is not a Failed Fix. The Engine does these things:

- It does not comment on the ticket, add a label or change its status. This applies to the current ticket and to all the tickets after it.
- It puts the outcome `left_for_next_run` in the run report for each of these tickets.
- It never throws away a finished fix. If the last call of a fix passes the ceiling, the Engine still publishes the fix. The next call does not start.

The cheap model name, the strong model name and the ceiling are settings.

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
| The order of the steps in an attempt, or when the Engine escalates | `fix/` |
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
2. `fix_ticket` starts an attempt with the cheap model. It opens the repository and reads `app.py`.
3. The model gets the first message. It calls `edit_file` and replaces `eval(input())` with `int(input())`.
4. The `WorkingCopy` checks the edit and writes it. The result is "Edit applied."
5. The model calls `finish`.
6. The Engine checks the change. One line changed. The file still parses.
7. The Engine commits, opens a draft pull request and comments on GR-100. GR-100 moves to In Review.

If the model calls `edit_file` on `.env`, the result is `Refused:` and nothing changes. The model can try another edit.
