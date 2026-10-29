# veil: what every file and every function does

This folder explains the `veil` code to a person who does not write code. It covers every file and every function. It describes the committed code at commit `55a0f8b`.

Read this page first. It tells the story of one run in plain words. Then it shows which part to open for which question.

## One run, in plain words

veil is an agent. It reads security tickets, fixes the code, and asks a person to review the fix. It never merges anything by itself.

1. A **Shell** starts a run. A Shell is the outer program: a GitHub Action or a service. The Shell hands the **Engine** everything it needs in one `Context`. The Context holds the settings, the ticket system, the code host, the model, and the Credentials of the run.
2. The Engine asks the **tracker** (Jira) for open tickets. Each ticket names a repository, a file, a line and a finding. A ticket also names the **Source PR branch**. That is the branch where the finding lives.
3. The Engine **skips** a ticket that it must not touch. It skips a ticket in four cases. The Source PR closed. A Fix exists. An earlier attempt failed. The ticket has no issue label.
4. The Engine **groups** the rest. Low and Medium tickets share one Fix PR. A High ticket gets its own PR. High tickets that change the same file share one.
5. For each group, the Engine asks the **repo provider** (GitHub) for a private copy of the Source PR branch.
6. For each ticket, the Engine starts a **conversation** with the cheap model. The model can read files, search, list folders and edit a file. It cannot run commands and it cannot reach the network. The model calls `finish` when its work ends.
7. Every edit passes **safety checks** before the Engine writes it. The Engine refuses edits to workflow files, lock files and key files. It refuses an edit that deletes a file or crosses 200 changed lines. It checks that Python, JSON and TOML files still parse.
8. The Engine **scans** the new text for Secrets. A Secret in the edit, the commit message or the explanation fails the attempt.
9. If the cheap attempt fails, the Engine tries **once more** with the strong model. If that attempt fails too, the ticket becomes a **Failed Fix**. The ticket stays open, gets a comment with the reason, and gets a marker label. The next run skips it.
10. A Fix that passes becomes one **commit**. The Engine opens one **draft Fix PR** for the group. The PR targets the Source PR branch. It never targets the default branch. The Engine comments on each ticket and sets its status to In Review.
11. A **token ceiling** limits the whole run. If the run reaches it, the Engine publishes the Fixes that passed. It leaves the other tickets for the next run.
12. The Engine hides every Credential value in everything it sends. It returns a **run report** to the Shell. The report lists what happened to each ticket.

## Which part to open

| Part | Open it to learn about |
|---|---|
| [02 The run and the fix](02-the-run-and-the-fix.md) | The entry point, the skip rules, the grouping, and the fix loop with its two attempts. |
| [03 Tools, safe edits and secrets](03-tools-edits-and-secrets.md) | What the model can do, how the Engine checks an edit, and how it finds and hides Secrets. |
| [04 The vocabulary](04-vocabulary-models-interfaces-errors-constants.md) | The records, the four interfaces, the errors and every fixed value. |
| [05 The GitHub adapter](05-github-adapter.md) | Checkouts, pushes, finding an existing Fix, and opening the draft PR. |
| [06 The Jira adapter](06-jira-adapter.md) | Searching for tickets, reading them, and changing labels, statuses and comments. |
| [07 The OpenAI adapter and shared HTTP code](07-openai-adapter-and-shared-http-code.md) | Talking to the model, and the HTTP rules that all three adapters share. |
| [08 The Engine tests](08-engine-tests.md) | What each Engine test proves and how a test builds a scenario. |
| [09 The adapter tests and the fakes](09-adapter-tests-and-fakes.md) | What each adapter test proves, and the stand-in parts that tests use. |

Each part has the same shape. "The flow" tells the story in order. "Files" lists every file and every function. "Things to know" lists sharp edges.

## The words you will meet

The file `GLOSSARY.md` at the top of the project defines the key words. They are Gozu Ticket, Fix, Fix PR, Source PR, Shared PR, High PR and Severity Bucket. It also defines Failed Fix, Engine, Shell, Credential, Secret and Token ceiling. This doc uses them the same way.

Three more words appear often. An **adapter** is a part that talks to an outside service. An **interface** is a list of methods that a part must have. A **fake** is a stand-in that behaves like the real part, for tests.

## Sharp edges that the readers checked in the code

- The tool results of `read_file` and `search` do not pass through redaction. A Secret inside a file that the model may read can reach the model.
- The Engine does not catch errors from the tracker, the repo provider or the model client. They leave `run` and go to the Shell.
- The Engine checks the token ceiling before each model call. A run can pass the ceiling by the size of one reply.
- The parse check covers `.py`, `.json` and `.toml` files only. A broken file of another type passes it.
- Only a shared group has a size cap. A group of High tickets that overlap has none.
- People wrote the Jira and OpenAI test answers by hand from public documents. Nobody recorded them from a live call.

## Not covered yet

The settings schema (ticket GR-21) is in progress in the working folder and not committed. Its files are not in this doc. They are the new `engine/config/` folder, `adapters/yaml_settings.py`, the `settings_*` constants and the settings tests. Update this doc after that work lands.
