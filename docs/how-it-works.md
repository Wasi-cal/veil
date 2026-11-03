# How veil works

This page explains what the code does, step by step. Read `GLOSSARY.md` for the terms.

## The short version

Veil takes open Gozu Tickets. Gozu makes a ticket when a developer raises a pull request and a scan finds a problem. We call that pull request the Source PR. Each ticket names one file and one line with a security finding. For each ticket, Veil asks an AI model to change the code. Then Veil opens a pull request. A human reviews the pull request.

The part that does this work is the Engine. You start it with one function call: `run(context)`.

Two diagrams show the flow: `docs/diagrams/how-veil-works.html` and `docs/diagrams/github-action-workflow.html`. Open them in a browser.

## What you give to the Engine

The `context` holds five parts:

- **settings**: the limits and the names, for example 25 steps, 200 changed lines and the label of a Failed Fix. `parse_settings` makes them from the repo file. See the section on settings and `docs/settings.md`.
- **tracker**: the place where the tickets are. In real use this is Jira.
- **repo provider**: gives a copy of the repository and opens pull requests. In real use this is GitHub.
- **model client**: talks to the AI model.
- **secrets**: the credential values of this run, for example the GitHub token and the OpenAI key. The Shell passes them in. The Engine uses them to find and hide secrets. The Engine never reads them from the environment.

The Engine knows only the shape of these parts. It does not know Jira, GitHub or OpenAI. In the tests, fakes take their place. The real parts come in later tickets (GR-18 to GR-20). This is why the tests need no network.

## What happens in one run

The function `run` works in four stages:

1. It skips the tickets that must not get a Fix (see the section "Which tickets the Engine skips").
2. It puts the other tickets into groups. Each group gets one pull request (see the section "How the Engine groups tickets"). High groups come first.
3. It fixes the tickets of each group, one after the other, in one checkout.
4. It opens one pull request for each group.

For one group, the steps are:

1. Open a copy of the repository. This is the branch of the Source PR. A group has one copy.
2. For each ticket of the group, read the file that the ticket names. Refuse if the file may hold secrets.
3. Build the first message to the model. It holds the repository, file, line, severity and finding. It also holds about 40 lines of code around the flagged line. The Engine marks the text from the ticket as untrusted data.
4. Talk to the model. The model answers with tool calls. The Engine runs each call and sends the result back. This repeats until the model calls `finish`. Before each model call, the Engine checks the token cap of the ticket.
5. The model gives four things with `finish`: a commit message and three parts. The commit message is a Conventional Commit of at most 72 characters, for example `fix(security): replace eval with a safe parser`. The Engine adds the footer `Refs: <ticket>`. The part `problem` says why this code is a problem. The part `change` says what the model changed. The part `solves` says what the change solves. Each part has at most 3 sentences, and a sentence has at most 25 words. A part that copies the text of the ticket is refused. The prompt asks the model to write in ASD-STE100. The Engine checks only the number of sentences and the length of a sentence. If the format is wrong, the Engine gives an error and the model can try again.
6. Check the change. It must not be empty. It must have 200 changed lines or fewer. Each edited file must still parse. The added lines, the commit message and the explanation must hold no secret (see the section "Secrets"). Then the Engine makes one commit for this Fix. The next ticket starts from that commit, so it sees the earlier Fixes.
7. After the last ticket, publish. The Engine opens one pull request that targets the branch of the Source PR. The title is the commit subject and the ticket, or `fix(security): resolve N findings (…)` for many tickets. The body has a summary, then one section for each ticket. A section has the three parts of the Fix under the labels "Why this is a problem", "What changed" and "What this solves". The Engine also adds a comment with the link and the same three parts on each ticket. It moves each ticket to In Review.

If the first attempt fails, the Engine starts one more attempt with the strong model (see the section "When an attempt fails").

## How the Engine groups tickets

The Engine gives each ticket a Severity Bucket from the severity map. The map is a setting. A map that you give changes only its own words. The other words keep the default. The default map is:

| Gozu severity | Bucket |
|---|---|
| `BLOCKER`, `CRITICAL`, `HIGH` | High |
| `MAJOR`, `MEDIUM` | Medium |
| `MINOR`, `INFO`, `LOW` | Low |

A severity word that is not in the map is High. The bucket sets only the order of the PRs. High goes first.

| Tickets | Group |
|---|---|
| One ticket | One PR. The severity does not matter. |
| Same file | Tickets that flag the same file in the same Source PR go into one PR, because their Fixes overlap. The body of the PR gives the reason. |

There is no cap. One hundred tickets on one hundred files give one hundred PRs. The PRs run in this order: High, then Medium, then Low. PRs of equal rank keep the order of the tickets.

Other rules:

- A Failed Fix stays out of the PR. The PR holds only the Fixes that passed. A ticket that ends as a Failed Fix leaves no edit in the PR.
- A ticket that uses its token cap in the middle of a group becomes a Failed Fix. The Fixes that passed are still published. The later tickets of the group go on.
- The branch of a PR starts with the branch prefix (setting `branch_prefix`, default `gozu/fix-`) and the key of the first Fix that passed. A ticket that failed gives no name. So a later run can make a new PR for that ticket without a branch clash.
- Every PR opens ready for review. The Engine merges nothing.

## Which tickets the Engine skips

The tracker gives the Engine the candidates: tickets that are open, unassigned and marked by Gozu. The Engine checks all candidates up front, before it opens any checkout. The Engine skips a ticket for one of these reasons:

| Reason in the report | What it means |
|---|---|
| `raised_against_fix_branch` | The finding is on a Fix branch. That is a branch that starts with `gozu/fix-` or with the setting `branch_prefix`. A human decides what happens to it. |
| `failed_fix` | The ticket has the label `veil-failed-fix`. It stays untouched until a human deletes the label. |
| `ignored_path` | The file of the ticket is inside `.github/`, at any depth. Gozu makes no ticket for these files now. This catches an older ticket. |
| `no_issue_label` | The ticket has no label that starts with `issue-`. The Engine cannot prove that no PR exists. |
| `source_pr_not_open` | The branch of the ticket has no open PR. The developer merged or closed the Source PR, or the branch never had a PR. |
| `duplicate_issue` | An earlier ticket in this run has the same issue label on the same Source PR branch. It is the same finding, so the Engine keeps the first ticket. |
| `open_pr` | The repo provider has an open PR with the Source PR branch as its base. The PR carries the issue label of the ticket. |
| `fix_branch` | The repo provider has a Fix branch that carries the issue label. No PR is open. |

A skipped ticket opens no checkout, uses no tokens and gets no comment. The run report lists each skipped ticket under its reason.

The run report has a table with one row for each ticket: the ticket, the outcome and the reason. A Failed Fix has the same reason in the report as in its Jira comment. The Engine hides credentials in the reason.

This makes a second run safe. The Engine puts the issue label on each PR that it opens. The next run finds the PR and skips the ticket. The Engine skips a Failed Fix ticket too, so it gets no second comment. After a run that stopped at the token ceiling, the next run fixes only the tickets that the earlier run left.

If the tracker lists a ticket twice, the Engine uses it once. If two tickets have the same issue label on the same Source PR branch, the Engine fixes the first one. It skips the second because the first PR already exists.

## When an attempt fails

An attempt fails at the step cap, when the model calls `finish` and made no change, or when an edited file does not parse. Then the Engine starts one more attempt with the strong model. This second attempt has these rules:

- It starts from the last commit of the group. The Engine discards the edits of the first attempt, so none of them stays.
- It gets only the reason of the failure, in its first message. It does not get the other messages of the first attempt.
- It is the last attempt. There is no third attempt.

A ticket file that the Engine cannot read does not start a second attempt. The model never ran, so the strong model cannot do better.

## Failed Fix

A Failed Fix happens when the second attempt fails too. The Engine then does three things:

1. It adds a comment on the ticket with the reason of each attempt.
2. It adds the label `veil-failed-fix`.
3. It keeps the ticket open.

The Engine then goes on with the next ticket. A Failed Fix is not an error. The run does not stop.

## The token cap of a ticket

The Engine counts the tokens that the model API reports. Each ticket has its own count. The count holds all attempts of that ticket. The default cap is 100,000 tokens for each ticket. There is no cap for the whole run.

Before each model call, the Engine checks the count of the ticket. If the count is at the cap, the Engine stops the work on that ticket. The ticket becomes a Failed Fix:

- The Engine drops the edits of the ticket.
- It adds the label `veil-failed-fix` and a comment with the reason. The ticket stays open.
- The run goes on with the next ticket. The next ticket has a new count.
- It never throws away a finished fix. If the last call of a fix passes the cap, the Engine still publishes the fix. The next call does not start.

The run report still shows the tokens that all tickets used.

The cheap model name, the strong model name and the cap are settings.

## The GitHub Action Shell

The Action is the first Shell (ADR 0013). It runs the Engine once for the repo of the workflow. `run_action(environ)` is its entry point.

1. It reads the repo, the workspace and the event from the runner. It loads `.gozu/jira-to-pr.yml` as the repo settings.
2. It checks the event. `schedule`, `workflow_dispatch`, `repository_dispatch` and `pull_request` may run. Each one needs its setting to be on. Any other event fails. A `pull_request` event runs only for a PR from this repo. The Action reads the head of the PR from the event file of the runner. A PR from a fork or from a deleted repo ends the run with a notice, before the Action reads a secret. A run on a PR sees only the tickets of the branch of that PR.
3. It reads the Jira and OpenAI credentials from the variables that the settings name. It reads the `GITHUB_TOKEN` of the workflow. It masks all three in the log.
4. It builds the context from them. The token covers this repo for this job only.
5. It builds the context, runs the Engine, closes the checkouts and writes the run report to the step summary.

Any failure before step 5 stops the run with one error line and exit code 1. No ticket changes. A Failed Fix is not a failure.

A ticket needs all of these before the Action fixes it:

- The label `veil-eligible`, or the label that the setting `eligible_label` names. If you set `eligible_label` to an empty text, a ticket needs no such label. Then veil takes every open ticket without an assignee in the project keys.
- A label that starts with `issue-`. It names the finding. The Engine copies it to the Fix PR. A title of the form `repo | file | line | title` and the other labels are in `docs/ticket-contract.md`.
- A Details list with the repository, the file (`Component`), the line, the severity and the exact branch. A branch is required. There is no unknown branch.
- An open PR from that branch in that repository.
- A status that is not done, and no assignee.

Two repo settings must fit the site. The Jira workflow must have the status that `in_review_status` names, or you must set the setting to a status that exists. The repo must allow GitHub Actions to create pull requests (Settings, Actions, General).

## The service Shell (deferred)

The org-wide service was to be the second Shell. It is not in the code now. veil runs on one repo through the GitHub Action. ADR 0017 keeps the decisions of the service. The code is deleted on purpose, and git history keeps it (commit `0bcf11c`).

## Settings

Every number and every name that the Engine uses is a setting. The model `Settings` holds them all, each with a default, a type and a range. `docs/settings.md` lists them. A test fails if a setting is missing from that file.

The settings of a run come from one file in the repo: `.gozu/jira-to-pr.yml`. A Shell reads the YAML with `load_settings_file` and gives a plain mapping to `parse_settings`. The Engine reads no file.

`parse_settings` checks every key. These fail: a key that is not a setting, a value of the wrong type and a value outside the range. A value that looks like a secret fails too. The failure comes before the Engine touches any ticket. The message lists every problem and never repeats a value.

A settings store in PostgreSQL with a Redis cache, and org settings above the repo file, are deferred (ADR 0017).

The safety rules are code. They are not settings. A setting with the name of a safety rule is an unknown key.

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

## Secrets

No secret may reach a commit, a PR, a Jira comment or a run report. The Engine uses two guards:

1. **The scan.** Before the Engine commits a Fix, it checks the files that the Fix edits, the commit message and the three parts. It looks for the credential values of this run. It also looks for these patterns. They are private key headers, AWS key ids, GitHub tokens, Google API keys, Slack tokens, keys that start with `sk-` and Atlassian API tokens. A match fails the attempt. The strong model gets one more try. The reason names the kind of secret and where it is. It never holds the value. The scan runs before the syntax check, so a parser error cannot repeat a secret. A secret that was already in a file does not count, because the Fix did not add it. So a Fix that edits a line next to an old key can pass.
2. **The redaction.** The Engine replaces each credential value and each text that matches a secret pattern with `[redacted]`. It does this in every text that it sends. These texts are the first prompt to the model and the PR title and body. They are also the commit message, every Jira comment, the reason of a Failed Fix and the run report. Two matches that overlap become one `[redacted]`. The Engine exports the function `redact`. Adapters and Shells use it for their own logs and errors.

The Engine does not change errors that leave `run()`, for example a git error with a token in it. The repo provider must redact those errors before it raises them. The real repo provider does this and raises `RepoProviderError`. See ADR 0007. The real Jira tracker does the same and raises `TrackerError`. See ADR 0008. The real model client does the same and raises `ModelClientError`. See ADR 0009.

A credential value must have at least 8 characters and must not be only white space. A shorter or blank value would change normal text when the Engine redacts, so the Context refuses it. The error message never shows the value.

## The safety rules

These rules are code. Settings cannot turn them off.

- The Engine never reads, lists, searches or edits anything in `.github/`. It never edits lockfiles or secret files.
- The Engine never opens a PR from or against the default branch of the repo. The repo provider asks GitHub for the name once for each repo, just before it pushes.
- The Engine never follows a symlink. A path that holds a symlink, in the file or in a folder of the path, is refused. A listing does not show symlinks. Without this rule, a symlink could hide `.github/` or `.env` behind a plain name.
- The Engine never creates or deletes a file.
- The Engine never reads `.env` files, keys or `.git/`.
- The Engine never touches a path outside the repository.
- The Engine never commits or sends a secret.
- The class `WorkingCopy` checks each edit before it writes the edit. A refused edit changes nothing.

## Where to find things

| You want to change | Open this folder |
|---|---|
| The order of the steps in an attempt, or when the Engine escalates | `fix/` |
| Which tickets the Engine skips | `eligibility/` |
| How tickets go into PRs | `grouping/` |
| What a tool does | `tools/handlers/` |
| A rule about paths, the diff limit or the syntax check | `workspace/` |
| How the Engine finds and hides secrets | `secrets/` |
| How the settings file is checked | `config/` |
| What the Engine needs from Jira, GitHub or the model | `interfaces/` |
| The shape of a ticket, a setting or the report | `models/` |
| A fixed value, such as a limit or a tool name | `constants/` (an adapter has its own `constants/`) |

A folder imports only from the folders below it. The file `run.py` is at the top. The folders `errors/` and `constants/` are at the bottom. A contract in `pyproject.toml` checks this.

## How the tests work

Almost every test calls `run(context)` with three fakes. The model fake plays a script of tool calls. The repo fake uses real local git repositories. The test then checks the result: pull requests, commits, ticket comments, labels and the report. The tests do not call the internal functions.

Example: the script says "edit one line, then finish". The test checks that one pull request exists and that the ticket is In Review.

## One example from start to end

Ticket GR-100 says: "Line 3 of `app.py` uses `eval(input())`."

1. `run` reads GR-100 from the tracker.
2. `fix_ticket` starts an attempt with the cheap model. It opens the repository and reads `app.py`.
3. The model gets the first message. It calls `edit_file` and replaces `eval(input())` with `int(input())`.
4. The `WorkingCopy` checks the edit and writes it. The result is "Edit applied."
5. The model calls `finish`.
6. The Engine checks the change. One line changed. The file still parses.
7. The Engine commits, opens a pull request and comments on GR-100. GR-100 moves to In Review.

If the model calls `edit_file` on `.env`, the result is `Refused:` and nothing changes. The model can try another edit.
