# The run and the fix

This part covers the code that runs the whole job. It picks the Gozu Tickets that the Engine may fix, puts them into groups, and fixes each group. It then opens one draft Fix PR for each group and records what happened. The Engine does all of this without knowing which Shell started it.

Other parts of this doc cover the tools and edits that the model uses (part 03). They also cover the models, interfaces, errors and constants (part 04) and the real adapters (parts 05 to 07). This part names them and does not describe them.

## The flow

1. The Shell builds a `Context` (in `context.py`). It holds the settings, the tracker, the repo provider, the model client and the Credentials of the run. The Shell then calls `run(context)` in `run.py`.
2. `run` makes an empty `RunReport`. It asks the tracker for the open tickets. `distinct` in `eligibility/select.py` drops a ticket that the tracker listed twice.
3. `select_eligible` checks each ticket with `_skip_reason`. A ticket that fails a check goes in the report as skipped, with the reason. The Engine does not touch it again.
4. `plan_groups` in `grouping/plan.py` puts the eligible tickets into groups. It uses `bucket_of` in `grouping/severity.py` to find the Severity Bucket of each ticket. High groups come first. Shared groups come next.
5. A shared group holds at most `shared_pr_max` tickets (10 by default). `run` calls `leave_for_next_run` (in `fix/left_over.py`) for the tickets above that cap. They get the outcome `left_for_next_run` and no change in the tracker.
6. `run` calls `fix_group` (in `fix/group.py`) for each group, one after the other. `fix_group` first calls `ensure_budget` (in `fix/budget.py`). This is the first place where the Token ceiling applies. Then it asks the repo provider for one workspace (a checkout) of the Source PR branch.
7. For each ticket of the group, `fix_group` calls `fix_ticket` (in `fix/escalation.py`). `fix_ticket` calls `attempt` (in `fix/attempt.py`) with the cheap model.
8. `attempt` calls `ensure_budget` again. It reads the file of the ticket and builds the prompts with `system_prompt` and `first_prompt` (in `fix/prompt.py`). It hides Credential values in the user prompt. Then it calls `converse` (in `fix/conversation.py`).
9. `converse` is the loop with the model. Before each model call it calls `ensure_budget`. After each reply it adds the tokens of that reply to `tokens_used` in the report. It runs each tool call of the model through the `Toolbox`. The tools themselves are in part 03.
10. The step cap applies inside `converse`. The cap is 25 steps by default. A step is one tool call. An empty reply also counts as one step. At the cap, `converse` raises `AttemptFailed`.
11. The loop ends when the model calls `finish` with valid arguments. `read_finish` (in `fix/finish.py`) checks them. A bad `finish` call gets an error text, and the model can try again. A bad call counts as a step.
12. `attempt` then calls `ensure_no_secret` (in `fix/secret_check.py`). It refuses a Fix that adds a Secret to a file, to the commit message or to the explanation. It then calls `verify` on the working copy. `attempt` returns a `Fix`. The edits are not committed yet.
13. If the cheap attempt raises `AttemptFailed`, `fix_ticket` discards the edits. It then calls `attempt` once more with the strong model. It gives the reason of the first failure to the model as untrusted data. This is the escalation. There is no third attempt.
14. If the strong attempt also raises `AttemptFailed`, `fix_ticket` discards the edits and raises `FailedFix`. This is where a Failed Fix starts. `attempt` can also raise `FailedFix` at once if the Engine cannot read the file.
15. `fix_group` catches `FailedFix` and calls `record_failed_fix` (in `fix/failures.py`). It adds the marker label to the ticket, then adds a comment with the reason. The ticket stays open and out of the PR. The next run skips it because of the label.
16. If `attempt` returns a `Fix`, `fix_group` gives the branch of the Fix PR a name with `branch_name` on the group. It does this once, for the first Fix that passed. It then commits the Fix on that branch with a redacted commit message.
17. If the run hits the token ceiling during the loop over tickets, `ensure_budget` raises `BudgetExhausted`. `fix_group` discards the edits that it did not commit. It still publishes the Fixes that it committed before. Then it raises `BudgetExhausted` again.
18. After the loop, `fix_group` calls `publish` (in `fix/publish.py`) if at least one Fix passed. `publish` opens one draft Fix PR with `pr_body` and `ticket_comment` (in `fix/pr_text.py`). It comments on each ticket and sets the status to In Review. It records the outcome `fixed` and saves the URL of the PR in the report.
19. If `fix_group` raised `BudgetExhausted`, `run` stops the loop. It marks every planned ticket without an outcome as `left_for_next_run`. They stay untouched in the tracker.
20. `run` returns the report. Before that, it calls `redacted` on the report so that no Credential value leaves the Engine.

## Files

### `engine/__init__.py`

The public face of the Engine. A Shell imports everything it needs from this one place. The file has no functions. It re-exports these names: `Context`, `DraftPr`, `FixQuery`, `ModelClient`, `ModelReply`, `RepoProvider`, `RunReport`, `Settings`, `Ticket`, `ToolCall`, `ToolDefinition`, `Tracker`, `Workspace`, `redact` and `run`. The listed names come from other files, which other parts describe.

### `engine/run.py`

The entry point of the Engine. It exists as its own file. A Shell then has one call to make, and the order of the steps sits in one place.

- `run(context)` — fixes the eligible Gozu Tickets and returns the report of the run. It selects, groups and fixes each group in turn. It stops at the token ceiling. In goes a `Context`. Out comes a `RunReport` with every text redacted. The Shell calls it.

### `engine/context.py`

The bag of things that one run needs. It exists as its own file so that the Engine receives all outside parts and all Credentials in one checked record.

- `Context` — a pydantic model (a checked record) that nobody can change after creation. It hides the input of a validation error, so an error never repeats a Credential value.
  - `settings` — the settings of the run, such as the token ceiling and the step cap.
  - `tracker` — the part that talks to the ticket system.
  - `repo_provider` — the part that talks to the code host.
  - `model_client` — the part that talks to the model.
  - `credentials` — the Credential values of the run, kept as hidden values. The default is an empty list.
- `_long_enough(credentials)` — a check that runs when the Shell creates a `Context`. It refuses a Credential value shorter than 8 characters. It also refuses a value that has only white space. The error message never shows a value. In goes the tuple of Credentials. Out comes the same tuple.
- `Context.redact(text)` — replaces the Credential values of this run, and the known Secret patterns, in a text. In goes a text. Out comes the text with those parts hidden. Every text that leaves the Engine goes through it.
- `Context.credential_values` — a property. It gives the Credential values as plain text. The Engine uses them only to scan and to redact.

### `engine/eligibility/select.py`

The rules that decide which tickets the Engine may fix. It exists as its own file so that all skip rules sit in one place.

- `distinct(tickets)` — keeps the first ticket for each key and drops the rest. A tracker can list a ticket twice. In goes a list of tickets. Out comes a shorter list. `run` calls it.
- `select_eligible(tickets, repo_provider, settings, report)` — returns the tickets that the Engine may fix. For each other ticket, it writes the outcome `skipped` and the reason in the report. Two tickets with the same issue label on one Source PR branch count as one finding. The Engine keeps the first. `run` calls it.
- `_skip_reason(ticket, repo_provider, settings, issues_in_this_run)` — gives the reason why the Engine must not fix a ticket, or nothing if it may. The checks run in this order, and the cheap ones come first. First, the ticket is about a Fix branch. Second, the ticket has the Failed Fix label. Third, the ticket has no issue label. Fourth, the issue is a duplicate in this run. Fifth, the Source PR is not open. Sixth, a Fix for this issue exists already. `select_eligible` calls it.

### `engine/grouping/severity.py`

The map from a severity word to a Severity Bucket. It exists as its own file because both the plan and the settings depend on one rule for it.

- `bucket_of(severity, severity_map)` — gives the Severity Bucket (high, medium or low) of a severity word. It removes white space and makes the word upper case before it looks in the map. A word that is not in the map counts as high. Then the ticket gets its own PR and a person looks at it. `plan_groups` calls it.

### `engine/grouping/plan.py`

The rules that decide which tickets share a Fix PR. It exists as its own file so that the grouping is easy to test without a model.

- `plan_groups(tickets, settings)` — puts the tickets into groups and returns a `GroupPlan`. A High ticket goes into a high group. High tickets with the same repository, the same Source PR branch and the same file share one group, because their Fixes overlap. The plan first cleans the file path, so a path with `\` or `./` matches. Low and Medium tickets with the same repository and the same branch share one shared group. A shared group holds at most `shared_pr_max` tickets. The other tickets go in `left_for_next_run`. High groups come before shared groups. A high group with more than one ticket carries a reason text that names the file. `run` calls it.

### `engine/fix/left_over.py`

A tiny helper that marks tickets as waiting. It exists as its own file because both `run` and the cap on a shared group use it.

- `leave_for_next_run(tickets, report)` — gives each ticket the outcome `left_for_next_run` in the report. It does not change anything in the tracker. In go a list of tickets and the report. Nothing comes out. `run` calls it.

### `engine/fix/budget.py`

The check for the token ceiling. It exists as its own file because three other files call the same rule.

- `ensure_budget(report, settings)` — raises `BudgetExhausted` if the tokens that the run used equal or exceed the token ceiling (100,000 by default). Otherwise it does nothing. `fix_group`, `attempt` and `converse` call it.

### `engine/fix/group.py`

The work for one group. It exists as its own file because it ties together the checkout, the commits and the PR.

- `fix_group(context, group, report)` — fixes the tickets of one group in one checkout. It commits each Fix, then opens one draft Fix PR. A Failed Fix stays out of the PR. At the token ceiling it discards the edits that are not committed. It publishes the Fixes that passed. Then it raises `BudgetExhausted`. `run` calls it.

### `engine/fix/escalation.py`

The rule that moves from the cheap model to the strong model. It exists as its own file so that the rule of "one retry" is in one place.

- `fix_ticket(context, ticket, report, workspace)` — tries the cheap model. If the attempt fails, it discards the edits and tries the strong model once. It gives the strong model the first failure reason, with Credential values hidden. If both attempts fail, it discards the edits and raises `FailedFix`. The reason joins both failures. `fix_group` calls it.

### `engine/fix/attempt.py`

One try at one ticket with one model. It exists as its own file because the first try and the second try run the same steps.

- `attempt(context, ticket, report, model, workspace, failure=None)` — tries to fix one ticket with the named model. It reads the file, builds the prompts, runs the loop, checks for Secrets and verifies the change. It returns a `Fix`. The edits stay in the workspace and are not committed. It raises `AttemptFailed` if the attempt fails after the model started. It raises `FailedFix` if the file is on the refused list, is missing, is a folder or is not text. `fix_ticket` calls it.

### `engine/fix/prompt.py`

The text that the Engine sends to the model. It exists as its own file so that the wording and the safety wrapping stay together.

- `_inert(text)` — breaks each closing tag of an untrusted block, so that the text cannot end the block early. In goes a text. Out comes the text with `</tag` changed to `<\/tag`. `first_prompt` calls it.
- `system_prompt(settings)` — gives the system prompt. It fills in the largest number of sentences for the explanation. In goes the settings. Out comes a text. `attempt` calls it.
- `first_prompt(ticket, source, failure=None)` — builds the first user message. It lists the repository, the file, the line and the severity. It adds the finding and an excerpt of the file around the ticket line, 20 lines on each side. It wraps the finding, the excerpt and the earlier failure reason in tags that mark them as untrusted data. It tells the model not to follow instructions in them. If the line is outside the file, it moves the line into the file. `attempt` calls it.

### `engine/fix/conversation.py`

The loop between the Engine and the model. It exists as its own file because it holds the step cap and the token count.

- `converse(model_client, model, toolbox, messages, settings, report)` — runs the tool calls of the model until it calls `finish` with valid arguments. It returns those arguments as `FinishArgs`. It adds the tokens of each reply to the report. A bad `finish` call gets an error text. It raises `AttemptFailed` at the step cap. It raises `BudgetExhausted` before a model call if the run used its token ceiling. `attempt` calls it.
- `_step_cap_reached(cap)` — builds the `AttemptFailed` error that says the attempt used the cap and did not finish. In goes the cap. Out comes the error. `converse` calls it.
- `_assistant_message(reply)` — builds the message that records the tool calls of the model, in the chat format. In goes a `ModelReply`. Out comes a message record. `converse` calls it.
- `_tool_message(call_id, content)` — builds the message that gives a tool result back to the model. In go the call id and the text. Out comes a message record. `converse` calls it.

### `engine/fix/finish.py`

The check of the `finish` call. It exists as its own file so that the rules on the commit message and the explanation are in one place.

- `count_sentences(text)` — counts the sentences of a text. A mark of `.`, `!` or `?` that white space or the end of the text follows ends a sentence. A text with no end mark counts as one sentence. `read_finish` calls it.
- `_abbreviation(text, mark)` — checks if a mark ends an abbreviation such as `etc.`. The known abbreviations are `e.g.`, `i.e.`, `etc.`, `vs.` and `cf.`. An abbreviation does not end a sentence. `count_sentences` calls it.
- `read_finish(call, settings)` — reads the arguments of a `finish` call. If they are valid, it returns a `FinishArgs`. If the format is wrong or the explanation has too many sentences, it returns an error text for the model. The limit is 3 sentences by default. `converse` calls it.

### `engine/fix/secret_check.py`

The Secret check for a finished attempt. It exists as its own file so that the rule "a Fix never holds a Secret" has one clear home.

- `ensure_no_secret(context, working_copy, finish)` — raises `AttemptFailed` if the Fix adds a Secret to a file, to the commit message or to the explanation. A Secret that was already in the file does not count. The reason names the kind of Secret and where it is. It never holds the value. `attempt` calls it.
- `_held(where, kind)` — builds the `AttemptFailed` error for a found Secret. In go a place and a kind. Out comes the error. `ensure_no_secret` calls it.

### `engine/fix/failures.py`

The record of a Failed Fix. It exists as its own file so that the order of the two tracker calls is in one place.

- `record_failed_fix(context, ticket, failed, report)` — leaves the ticket open. It adds the marker label `veil-failed-fix`, then adds a comment that starts with "Failed Fix." and gives the reason. It sets the outcome to `failed`. The label comes first. If the comment fails, the next run still skips the ticket and writes no second comment. `fix_group` calls it.

### `engine/fix/publish.py`

The step that opens the Fix PR and tells the tickets. It exists as its own file because it is the only step that changes things outside the checkout, apart from failures.

- `publish(context, group, fixes, branch, report)` — opens one draft Fix PR for the Fixes of a group. The PR has the Source PR branch as its base. The title, the body and the labels come from the Fixes. It redacts the title and body. Then for each Fix it adds a comment to the ticket, sets the status to In Review and records the outcome `fixed`. It adds the PR URL to the report. If the list of Fixes is empty, it does nothing. `fix_group` calls it.

### `engine/fix/pr_text.py`

The wording of the PR body and of the ticket comment. It exists as its own file so that the text is easy to change without touching the flow.

- `pr_body(group, fixes)` — builds the body of the PR. It has one paragraph for each Fix with the ticket key and the explanation. If the group has a reason and more than one Fix passed, the reason comes first. `publish` calls it.
- `ticket_comment(pr_url, fix)` — builds the comment for a ticket. It gives the link to the PR, then the explanation of the Fix. `publish` calls it.

## Things to know

- The Token ceiling is a check, not a hard stop in the middle of a call. The Engine adds the tokens after each reply and checks before the next call. A run can go past the ceiling by one reply.
- When the run hits the ceiling, it keeps the commits that already passed and publishes them. The Engine discards edits that it did not commit. Every ticket without an outcome gets `left_for_next_run`. That includes the ticket that was in progress.
- The step cap counts every tool call, a bad `finish` call and an empty reply. A model cannot loop for ever. After a second failure the ticket becomes a Failed Fix and a human must ask for another attempt.
- The code applies the secret rules in several places. `attempt` scans the edits, the commit message and the explanation. `Context.redact` runs on the prompt, the commit message, the PR title and body, the comments and the final report. The `Context` refuses a Credential value shorter than 8 characters.
- A severity word that the map does not know counts as high. That gives the ticket its own PR for a person to read. The plan caps only shared groups. A high group has no cap.
- `fix_group` does not catch an error from the tracker or the repo provider. If `add_label`, `add_comment`, `commit` or `open_draft_pr` raises, the error leaves `run`. The tickets already recorded keep their outcome, but the report is lost.
