# The vocabulary: models, interfaces, errors and constants

This part covers the words that the rest of the Engine uses. A model is a checked record of data. An interface is a list of methods that an outside part must have. An error is a named stop signal. A constant is a fixed value. The other parts of the Engine build on these four groups. Part 02 (run and fix) uses them to move a ticket to a Fix. Part 03 (tools, edits, secrets) uses the tool arguments, the path rules and the secret patterns. Parts 05 to 07 (adapters) fill the interfaces.

## The flow

1. The Shell starts a run. A Shell is a way to run the Engine. The Shell gives the Engine its parts and a `Settings` record. `Settings` holds the limits of the run. Its defaults come from `constants/limits.py`, `constants/model_names.py`, `constants/branches.py` and `constants/severity.py`.
2. The Engine asks the `Tracker` for `open_tickets`. The `Tracker` is the first of four plugs. A plug is an interface that a Shell or an adapter fills. An adapter is a part that talks to an outside service. The `Tracker` returns `Ticket` records. A `Ticket` holds the key, repository, file, line, severity, finding, Source PR branch and labels of one Gozu Ticket.
3. The Engine skips some tickets. It uses the `Ticket` labels, the `FixQuery` record and the `RepoProvider` plug. It writes each skip into the `skipped` field of the `RunReport`, with a reason from `constants/skip_reasons.py`. The `RepoProvider` is the second plug. It answers `has_open_pr` and `find_existing_fix`. The answer to `find_existing_fix` is a `FixKind` from `constants/fix_kinds.py`.
4. The Engine reads the severity of each ticket and finds its bucket with the severity map in `Settings`. It puts the tickets into `FixGroup` records. The kind of a group is `shared` or `high`, from `constants/group_kinds.py`. A `GroupPlan` holds the groups for this run and the tickets that wait for the next run.
5. For each group, the `RepoProvider` opens a `Workspace` with `open_workspace`. The `Workspace` is the third plug. It is a private checkout of the Source PR branch. The Engine reads, writes and commits files through it.
6. For each ticket, the Engine builds a prompt from `constants/prompt.py`. It wraps the ticket text and the file text in the untrusted tags. The Engine sends the messages to the `ModelClient` with `next`. The `ModelClient` is the fourth plug. It returns a `ModelReply`. The reply holds a list of `ToolCall` records and the token count. The Engine adds the tokens to the run total.
7. The Engine checks the arguments of each `ToolCall` with the records in `models/tool_args/`. A bad argument makes a checked record refuse the call. The tool names and the tool texts come from `constants/tools.py`. The `ToolDefinition` records tell the model which tools exist.
8. Edits break rules at times. The path rules raise `RuleViolation`. The edit step turns it into `EditRejected`. The model reads the message of `EditRejected` and tries again. No ticket fails at this point.
9. When the model calls `finish`, the `FinishArgs` record checks the commit message and the explanation. If the work is wrong, the Engine raises `AttemptFailed`. The Engine then tries the strong model once. Two failed attempts become `FailedFix`.
10. A good attempt gives a `Fix`. It holds the ticket, the commit message and the explanation. The Engine commits the Fix with `Workspace.commit`.
11. A `FailedFix` ends in a label and a comment on the ticket. The label is `veil-failed-fix`. The `Tracker` adds both. The `RunReport` records the outcome `failed` for the ticket.
12. After the last ticket of a group, the Engine builds a `DraftPr` from the `FixGroup` and the Fixes. The `FixGroup` gives the branch name and the title. The `RepoProvider` opens the draft PR with `open_draft_pr` and returns the URL. The Engine sets each fixed ticket to `In Review`.
13. If the run uses all of its tokens, the Engine raises `BudgetExhausted`. The Engine publishes the Fixes that passed. It marks the other tickets `left_for_next_run`. It then stops.
14. At the end, the Engine returns the `RunReport`. The method `RunReport.redacted` hides each secret in the report before the Shell sees it.
15. An error from an adapter (`TrackerError`, `RepoProviderError`, `ModelClientError`) is not caught in the Engine code of this snapshot. It leaves the run and goes to the Shell.

## Files

### constants/limits.py

This file holds the numbers that limit a run. It is its own file so that `Settings` and the code share one source for each default.

- `STEP_CAP` — 25. The most steps that the model may take in one attempt.
- `DIFF_LIMIT` — 200. The most changed lines that one Fix may have.
- `READ_FILE_MAX_LINES` — 300. The most lines that one `read_file` call returns.
- `SEARCH_MAX_MATCHES` — 50. The most matching lines that one `search` call returns.
- `TOOL_RESULT_MAX_BYTES` — 8192 bytes (8 times 1024). The most bytes in one tool result.
- `TOKEN_CEILING` — 100,000. The most tokens that one run may use. The glossary calls it the Token ceiling.
- `EXPLANATION_MAX_SENTENCES` — 3. The most sentences in the explanation of a Fix.
- `SHARED_PR_MAX` — 10. The most Fixes in one Shared PR.
- `MIN_SECRET_LENGTH` — 8. The least length of a credential value. `engine/context.py` refuses a shorter value, because a short value would hide too much text.
- `MIN_TOOL_RESULT_MAX_BYTES` — 256. The least value that `Settings` accepts for the tool result size.

### constants/labels.py

This file holds the two label words that the Engine uses on tickets.

- `ISSUE_LABEL_PREFIX` — the text `issue-`. A label that starts with it names the scan finding. `Ticket.issue_label` looks for it.
- `FAILED_FIX_LABEL` — the text `veil-failed-fix`. The Engine adds it to a Failed Fix. Later runs skip a ticket with this label.

### constants/outcomes.py

This file holds the four words for what happened to a ticket. The `RunReport` stores them in `outcomes`.

- `FIXED` — the text `fixed`. The ticket has a Fix in a PR.
- `FAILED` — the text `failed`. The ticket is a Failed Fix.
- `LEFT_FOR_NEXT_RUN` — the text `left_for_next_run`. The Engine did not touch the ticket in this run.
- `SKIPPED` — the text `skipped`. The ticket did not pass the checks. The reason is in `skipped`.

### constants/skip_reasons.py

This file holds the five reasons to skip a ticket. They are the keys of `RunReport.skipped`.

- `RAISED_AGAINST_FIX_BRANCH` — the text `raised_against_fix_branch`. The ticket belongs to a Fix branch. The glossary says that a human decides about such a ticket.
- `FAILED_FIX` — the text `failed_fix`. The ticket has the Failed Fix label.
- `NO_ISSUE_LABEL` — the text `no_issue_label`. The ticket has no label that starts with `issue-`.
- `DUPLICATE_ISSUE` — the text `duplicate_issue`. A Fix for this finding exists already.
- `SOURCE_PR_NOT_OPEN` — the text `source_pr_not_open`. The Source PR of the ticket is not open.

### constants/fix_kinds.py

This file names the two kinds of existing Fix that the repo provider can find.

- `FixKind` — a type. A value is `open_pr` or `fix_branch`. The comment says that a kind is also the reason to skip the ticket.
- `OPEN_PR` — the text `open_pr`. An open PR carries the issue label and has the Source PR branch as its base.
- `FIX_BRANCH` — the text `fix_branch`. A branch with the branch prefix carries the issue label.

### constants/group_kinds.py

This file names the two kinds of Fix group.

- `GroupKind` — a type. A value is `shared` or `high`.
- `SHARED_GROUP` — the text `shared`. A group for Low and Medium tickets.
- `HIGH_GROUP` — the text `high`. A group for High tickets.

### constants/severity.py

This file holds the severity buckets and the default map from severity words to buckets.

- `Bucket` — a type. A value is `high`, `medium` or `low`.
- `HIGH`, `MEDIUM`, `LOW` — the three bucket values `high`, `medium` and `low`.
- `DEFAULT_SEVERITY_MAP` — a map from a severity word to a bucket. `BLOCKER` and `CRITICAL` go to high. `MAJOR` goes to medium. `MINOR` and `INFO` go to low. The words `HIGH`, `MEDIUM` and `LOW` map to themselves.

### constants/branches.py

- `FIX_BRANCH_PREFIX` — the text `gozu/fix-`. Each Fix branch starts with it. `Settings` uses it as the default branch prefix.

### constants/statuses.py

- `IN_REVIEW` — the text `In Review`. The Engine sets this Jira status on a ticket after its Fix PR opens.

### constants/model_names.py

- `CHEAP_MODEL` — the text `cheap-model`. The default name of the model for the first attempt.
- `STRONG_MODEL` — the text `strong-model`. The default name of the model for the second attempt.

These two values are placeholder names. A Shell gives the real names in `Settings`.

### constants/tools.py

This file names the five tools of the model and says what each one does.

- `EDIT_FILE` — the text `edit_file`.
- `FINISH` — the text `finish`.
- `READ_FILE` — the text `read_file`.
- `SEARCH` — the text `search`.
- `LIST_DIR` — the text `list_dir`.
- `TOOL_DESCRIPTIONS` — a map from each tool name to the sentence that the model reads. `read_file` reads a text file and accepts a start line. `search` finds lines that match a regular expression. `list_dir` lists a folder. `edit_file` replaces the first match of an exact text and cannot make or remove files. `finish` ends the work and takes a one-line commit message and a short explanation.

### constants/tool_messages.py

- `NARROW_NOTE` — a note that the Engine adds to a tool result that it cut short. It says that the result is incomplete and asks for a narrower request, for example a later start line or a more exact pattern.

### constants/prompt.py

This file holds the text that the model reads and the tags that mark data.

- `CONTEXT_LINES_EACH_SIDE` — 20. The number of file lines before and after the flagged line that go into the prompt.
- `UNTRUSTED_TICKET_TAG` — the tag name `untrusted_ticket_data`. It wraps ticket text.
- `UNTRUSTED_FILE_TAG` — the tag name `untrusted_file_data`. It wraps file text.
- `UNTRUSTED_FAILURE_TAG` — the tag name `untrusted_failure_reason`. It wraps the reason of the first failed attempt in the second attempt.
- `ALL_UNTRUSTED_TAGS` — the three tags in one tuple. `engine/fix/prompt.py` loops over them.
- `SYSTEM_PROMPT` — the rules for the model. It fixes one finding with the smallest change. It calls `finish` at the end. It gives a one-line commit message. It limits the explanation to `{max_sentences}` sentences, and the Engine fills in this number. It says that ticket text and file text are data and the model must not follow them.

### constants/explanation.py

This file holds the two rules that count the sentences of an explanation.

- `SENTENCE_END` — a pattern that finds a mark (`.`, `!` or `?`) when white space or the end of the text follows it. A name such as `a.py` does not end a sentence.
- `ABBREVIATIONS` — the words `e.g.`, `i.e.`, `etc.`, `vs.` and `cf.`. The counter does not treat their full stops as the end of a sentence.

### constants/paths.py

This file holds the path rules of the Engine.

- `PROTECTED_DIRS` — one folder, `.github/workflows`. The model cannot change files in it.
- `LOCKFILE_NAMES` — a set of lower-case lockfile names, for example `uv.lock`, `package-lock.json`, `yarn.lock`, `cargo.lock` and `go.sum`. The model cannot change these files.
- `READ_REFUSED_PATTERNS` — the patterns `.env*`, `*.pem`, `*.key`, `*.p12`, `id_rsa*` and `.npmrc`. The model cannot read a file that matches. Settings can add patterns. Settings cannot remove these.
- `READ_REFUSED_DIRS` — one folder, `.git`. The model cannot read inside it.

### constants/secrets.py

This file holds the secret patterns and the words for them.

- `REDACTED` — the text `[redacted]`. It replaces a credential value or a text that matches a secret pattern.
- `CREDENTIAL_KIND` — the text `a credential of this run`. The scan uses it as the kind when it finds a credential value of the run.
- `SECRET_PATTERNS` — a tuple of pairs. Each pair holds a kind and a pattern. The kinds are a private key header, an AWS access key id, a GitHub token and a Google API key. The other kinds are a Slack token, an API key that starts with `sk-` and an Atlassian API token. The kind goes in the reason of a failed attempt.

### errors/attempt_failed.py

This file holds the error for one failed attempt. The model started, and the work did not pass.

- `AttemptFailed` — an error class. It is not a Failed Fix. Only a second failure becomes one.
- `AttemptFailed.__init__(reason)` — stores the reason text in the error and in the field `reason`. The workspace code raises it. `engine/fix/escalation.py` catches it.

### errors/edit_rejected.py

- `EditRejected` — an error class. An edit breaks a limit or a rule. The model reads the message and can try again. `working_copy.py` raises it. The `edit_file` handler catches it.

### errors/rule_violation.py

- `RuleViolation` — an error class. A path breaks a rule. The message names the rule. `path_rules.py` raises it. The tool handlers and `attempt.py` catch it.

### errors/failed_fix.py

- `FailedFix` — an error class. The Engine cannot fix a ticket within its limits. The `reason` goes in the comment on the ticket.
- `FailedFix.__init__(reason)` — stores the reason text in the error and in the field `reason`. `attempt.py` and `escalation.py` raise it. `engine/fix/group.py` catches it.

### errors/budget_exhausted.py

- `BudgetExhausted` — an error class. The run used its token ceiling. The Engine stops and does not touch the other tickets. `engine/fix/budget.py` raises it. `engine/fix/group.py` and `engine/run.py` catch it.

### errors/model_client_error.py

- `ModelClientError` — an error class. The model client could not get a reply. The adapter hides credential values in the message.
- `ModelClientError.__init__(message, retryable=False)` — stores the message and a `retryable` flag. The flag is True when the same call can work later, for example after a rate limit. The OpenAI adapter raises it.

### errors/repo_provider_error.py

- `RepoProviderError` — an error class. The repo provider could not do its task. The adapter hides credential values in the message. The GitHub adapter raises it.

### errors/tracker_error.py

- `TrackerError` — an error class. The tracker could not do its task. The adapter hides credential values in the message. The Jira adapter raises it.

### interfaces/tracker.py

This file holds the first plug, the `Tracker`. It lets the Engine work with any ticket system.

- `Tracker` — a Protocol. A Protocol is a list of methods that a part must have. The decorator `runtime_checkable` lets the code test a part against it.
- `Tracker.open_tickets()` — returns the candidate tickets. They are open, not assigned and have the Gozu label. Each `Ticket` carries its Source PR branch and all its labels. The labels show the Failed Fix label, so the next run skips that ticket. The Engine calls it at the start of a run.
- `Tracker.add_comment(key, text)` — adds a comment to the ticket with this key. Returns nothing.
- `Tracker.set_status(key, status)` — moves the ticket to a status, for example `In Review`. Returns nothing.
- `Tracker.add_label(key, label)` — adds a label to the ticket. Returns nothing.

### interfaces/repo_provider.py

This file holds the second plug, the `RepoProvider`. It lets the Engine work with any code host.

- `RepoProvider` — a Protocol with four methods.
- `RepoProvider.open_workspace(repo, branch)` — opens a private checkout of the branch of the Source PR and returns a `Workspace`. The branch name is data. The method must refuse a name that git can read as an option, for example a name that starts with a dash.
- `RepoProvider.has_open_pr(repo, branch)` — returns True if an open PR in the repository has this branch as its head. This is the Source PR of a ticket. A PR from a fork does not count.
- `RepoProvider.find_existing_fix(query)` — takes a `FixQuery` and returns the `FixKind` of the Fix that exists, or None. An open PR with the label and the Source PR branch as base gives `open_pr`. A branch with the prefix and the label gives `fix_branch`. If both exist, the answer is `open_pr`.
- `RepoProvider.open_draft_pr(draft)` — takes a `DraftPr`, pushes its branch, opens a draft PR against its base and returns the URL. It pushes only the Fix branch and never the base or the default branch. If a PR for the branch exists, it returns that URL and makes no second PR.

### interfaces/workspace.py

This file holds the third plug, the `Workspace`. It is the checkout in which the Engine reads and changes files.

- `Workspace` — a Protocol with five methods.
- `Workspace.read_file(path)` — returns the text of one file.
- `Workspace.list_files()` — returns the paths of all files in the checkout.
- `Workspace.write_file(path, content)` — replaces the text of one file. Returns nothing.
- `Workspace.commit(branch, message)` — commits all changes on this branch. It makes the branch from the current commit if the branch does not exist.
- `Workspace.discard_changes()` — throws away the changes that are not in a commit. The files go back to the last commit.

### interfaces/model_client.py

This file holds the fourth plug, the `ModelClient`. It lets the Engine work with any model service.

- `ModelClient` — a Protocol with one method.
- `ModelClient.next(messages, model, tools)` — sends the conversation and the tool definitions to the named model and returns a `ModelReply`. Each message has a role and either content or tool calls. An assistant message holds the calls of the model, each with an id. A tool message holds a result and the id of the call that it answers. The reply must give the id of each call and the tokens that the API counted.

### interfaces/\_\_init\_\_.py

This file exports the four plugs `ModelClient`, `RepoProvider`, `Tracker` and `Workspace`. A caller can import them from one place. It has no functions.

### models/ticket/ticket.py

This file holds the record of a Gozu Ticket.

- `Ticket` — a pydantic model. A pydantic model is a checked record. It is frozen, so no code can change it after it exists.
- `Ticket.key` — the ticket key in the tracker.
- `Ticket.repo` — the repository that the finding is in.
- `Ticket.file` — the path of the flagged file.
- `Ticket.line` — the flagged line number.
- `Ticket.severity` — the severity word of the finding, for example `CRITICAL`.
- `Ticket.finding` — the text of the finding. The Engine treats it as untrusted data.
- `Ticket.branch` — the branch of the Source PR.
- `Ticket.labels` — all labels of the ticket, in a tuple.
- `Ticket.issue_label` — a property. It returns the first label that starts with `issue-`, or None. Gozu sets it on each ticket. Selection and the Fix PR labels use it.

### models/config/settings.py

This file holds the settings of a run. The defaults are in code. The caller can give other values.

- `Settings` — a pydantic model. It is frozen. It refuses a field that it does not know.
- `Settings.cheap_model` — the name of the model for the first attempt. The default is `CHEAP_MODEL`. It must not be empty.
- `Settings.strong_model` — the name of the model for the second attempt. The default is `STRONG_MODEL`. It must not be empty.
- `Settings.token_ceiling` — the most tokens in one run. The default is 100,000. The least value is 1.
- `Settings.shared_pr_max` — the most Fixes in a Shared PR. The default is 10. The least value is 1.
- `Settings.branch_prefix` — the start of each Fix branch name. The default is `gozu/fix-`. It has at least 3 characters. It starts with a letter or a digit. It ends with `/` or `-`.
- `Settings.severity_map` — the map from severity words to buckets. The default is `DEFAULT_SEVERITY_MAP`.
- `Settings.step_cap` — the most model steps in one attempt. The default is 25. The least value is 1.
- `Settings.explanation_max_sentences` — the most sentences in an explanation. The default is 3. The least value is 1.
- `Settings.diff_limit` — the most changed lines in a Fix. The default is 200. The least value is 0.
- `Settings.tool_result_max_bytes` — the most bytes in a tool result. The default is 8192. The least value is 256.
- `Settings.read_file_max_lines` — the most lines in one file read. The default is 300. The least value is 1.
- `Settings.search_max_matches` — the most matches in one search. The default is 50. The least value is 1.
- `Settings.extra_refused_read_patterns` — more file patterns that the model cannot read. The default is none. They add to `READ_REFUSED_PATTERNS`.
- `Settings._safe_branch_prefix(value)` — a check that runs on `branch_prefix`. It refuses a value that holds `..`, `//` or `/.`. These could work as a path trick for git. It gives the value back if it is safe.
- `Settings._merge_with_defaults(value)` — a check that runs on `severity_map`. It starts with the default map. It then adds the given words in upper case, with white space removed. A given word replaces the default bucket of the same word. It returns the merged map.

### models/llm/tool_call.py

- `ToolCall` — a pydantic model. It is frozen. It is one call of a tool by the model.
- `ToolCall.name` — the name of the tool.
- `ToolCall.arguments` — a map of the arguments. The default is an empty map.
- `ToolCall.id` — the id from the API. The default is an empty text. The client copies it, because the answer must name it.

### models/llm/model_reply.py

- `ModelReply` — a pydantic model. It is frozen. It is one reply of the model.
- `ModelReply.tool_calls` — the list of `ToolCall` records in the reply.
- `ModelReply.tokens` — the tokens that the API counted for this reply. It cannot be below 0.

### models/llm/tool_definition.py

- `ToolDefinition` — a pydantic model. It is frozen. It describes a tool that the model can call.
- `ToolDefinition.name` — the name of the tool.
- `ToolDefinition.description` — the sentence that tells the model what the tool does.
- `ToolDefinition.parameters` — a JSON Schema of the arguments. A JSON Schema is a standard way to describe the shape of data.

### models/tool_args/read_file_args.py

- `ReadFileArgs` — a pydantic model for the `read_file` tool. It refuses a field that it does not know.
- `ReadFileArgs.path` — the path of the file to read.
- `ReadFileArgs.start_line` — the first line to read. The default is 1. It cannot be below 1.

### models/tool_args/search_args.py

- `SearchArgs` — a pydantic model for the `search` tool. It refuses a field that it does not know.
- `SearchArgs.pattern` — the regular expression to find.

### models/tool_args/list_dir_args.py

- `ListDirArgs` — a pydantic model for the `list_dir` tool. It refuses a field that it does not know.
- `ListDirArgs.path` — the folder to list. The default is `.`, the root of the repository.

### models/tool_args/edit_file_args.py

- `EditFileArgs` — a pydantic model for the `edit_file` tool. It refuses a field that it does not know.
- `EditFileArgs.path` — the path of the file to change.
- `EditFileArgs.old` — the exact text to replace.
- `EditFileArgs.new` — the text that goes in its place.

### models/tool_args/finish_args.py

- `FinishArgs` — a pydantic model for the `finish` tool. It is frozen. It refuses a field that it does not know.
- `FinishArgs.commit_message` — the commit message.
- `FinishArgs.explanation` — the short explanation of the Fix.
- `FinishArgs._one_line(value)` — a check on `commit_message`. It removes white space at both ends. It refuses an empty text and a text with a line break. It returns the clean text.
- `FinishArgs._not_empty(value)` — a check on `explanation`. It removes white space at both ends. It refuses an empty text. It returns the clean text.

### models/fix/fix.py

- `Fix` — a pydantic model. It is frozen. It is the result of one attempt that passed.
- `Fix.ticket` — the `Ticket` that the Fix addresses.
- `Fix.commit_message` — the one-line commit message.
- `Fix.explanation` — the explanation that the model gave.

### models/group/fix_group.py

- `FixGroup` — a pydantic model. It is frozen. It holds the tickets of one Fix PR. All tickets have the same repository and the same Source PR branch.
- `FixGroup.kind` — `shared` or `high`.
- `FixGroup.repo` — the repository of the group.
- `FixGroup.branch` — the Source PR branch of the group.
- `FixGroup.tickets` — the tickets of the group, in a tuple.
- `FixGroup.reason` — an optional text. The default is None.
- `FixGroup.branch_name(first_fixed_key, prefix)` — makes the name of the Fix branch. It writes the key in lower case after the prefix. A shared group adds `shared-` before the key. The key is the first ticket that passed. A failed ticket gives no name, so a later run can open a new PR without a branch clash. It returns the name.
- `FixGroup.title(keys)` — makes the title of the Fix PR. A high group gives `Fix` and the keys, joined with commas. A shared group gives `Fix` and the count of keys, then `tickets`. It returns the title.

### models/group/group_plan.py

- `GroupPlan` — a pydantic model. It is frozen. It is the plan of a run.
- `GroupPlan.groups` — the groups that the Engine fixes in this run.
- `GroupPlan.left_for_next_run` — the tickets that wait for a later run.

### models/provider/fix_query.py

- `FixQuery` — a pydantic model. It is frozen. It is the question to the repo provider: is there a Fix for this ticket?
- `FixQuery.repo` — the repository to search.
- `FixQuery.issue_label` — the issue label of the finding.
- `FixQuery.source_branch` — the Source PR branch. An open Fix PR must have it as its base.
- `FixQuery.branch_prefix` — the prefix of the Fix branches.

### models/provider/draft_pr.py

- `DraftPr` — a pydantic model. It is frozen. It holds what the repo provider needs to open a draft Fix PR. The PR targets the base and not the default branch.
- `DraftPr.repo` — the repository.
- `DraftPr.head` — the Fix branch. It starts with the branch prefix.
- `DraftPr.base` — the branch of the Source PR.
- `DraftPr.title` — the title of the PR.
- `DraftPr.body` — the text of the PR.
- `DraftPr.labels` — the labels of the PR, in a tuple. They are the issue labels of the fixed tickets.

### models/report/run_report.py

- `RunReport` — a pydantic model. It is not frozen. The Engine fills it during the run.
- `RunReport.pull_requests` — the URLs of the Fix PRs that the run opened.
- `RunReport.outcomes` — a map from ticket key to an outcome word from `constants/outcomes.py`.
- `RunReport.skipped` — a map from a skip reason to the list of ticket keys that have it.
- `RunReport.tokens_used` — the tokens that the run used. It starts at 0.
- `RunReport.redacted(redact)` — returns a copy of the report. It applies the `redact` function to each URL, each ticket key and each key in the skip lists. It does not change the skip reasons, the outcome words or the token count. `engine/run.py` calls it at the end of a run.

### models/\_\_init\_\_.py

This file exports `DraftPr`, `FixQuery`, `ModelReply`, `RunReport`, `Settings`, `Ticket`, `ToolCall` and `ToolDefinition`. A caller can import them from one place. It has no functions. It does not export the other records.

### src/veil/engine/models/__init__.py

This file lets a caller import the main models from one place. It has no functions.

- It lists `Settings`, `ModelReply`, `ToolCall`, `ToolDefinition`, `DraftPr`, `FixQuery`, `RunReport` and `Ticket`.

### src/veil/engine/interfaces/__init__.py

This file lets a caller import the four interfaces from one place. It has no functions.

- It lists `ModelClient`, `RepoProvider`, `Tracker` and `Workspace`.

## Things to know

- The Engine catches `TrackerError`, `RepoProviderError` and `ModelClientError` nowhere in this snapshot. A failure of an adapter ends the run and goes to the Shell. Only the `retryable` flag of `ModelClientError` tells a caller if a retry can work.
- A record in `models/` is frozen, except `RunReport` and the tool argument records for `read_file`, `search`, `list_dir` and `edit_file`. Those four refuse unknown fields but are not frozen.
- A `Settings` value cannot remove the default refused read patterns. `extra_refused_read_patterns` only adds to them.
- `Settings.branch_prefix` must end with `/` or `-`. It cannot hold `..`, `//` or `/.`. This stops a prefix that git could read as a path trick.
- `AttemptFailed` and `FailedFix` are two steps. One bad attempt gives `AttemptFailed`, and the strong model tries once. Only two bad attempts give `FailedFix`, the label and the comment.
- `CHEAP_MODEL` and `STRONG_MODEL` are placeholder names. A real run must give real model names in `Settings`.
