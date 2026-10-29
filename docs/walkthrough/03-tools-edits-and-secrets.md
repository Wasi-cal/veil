# Tools, safe edits and secrets

This part covers what the model can do to the repository and how the Engine keeps that safe. The model has four tools. They read, search, list and edit files. Every edit passes checks before the Engine writes it. The Engine also hides every Secret in the text that leaves it.

## The flow

1. The Engine gives the model a list of tools. `tool_definitions()` in `tools/definitions.py` builds this list. It holds the four tools of the `Toolbox`, then `finish`.
2. The model asks for a tool call. The `Toolbox.run()` method in `tools/toolbox.py` receives the call.
3. `Toolbox.run()` finds the tool in the `TOOLS` table. It checks the arguments of the call. If the tool is unknown or the arguments are wrong, it returns an error text. It never raises an error.
4. `Toolbox.run()` calls the handler of the tool. The handlers are in `tools/handlers/`. They are `read_file`, `search`, `list_dir` and `edit_file`.
5. The read handlers use `readable_path()` and `readable_files()` in `tools/handlers/readable.py`. These call `check_readable()` in `workspace/path_rules.py`. The model never sees a file that may hold Secrets.
6. `Toolbox.run()` passes the result to `cap_result()` in `tools/result_cap.py`. This cuts a long result and adds a note that tells the model to ask for less.
7. For an edit, `edit_file()` calls `WorkingCopy.edit()` in `workspace/working_copy.py`. The `WorkingCopy` runs its checks in this order. First `check_editable()` checks the path rules. Then it reads the file and refuses if the file does not exist. Then it refuses if the old text is not in the file. Then it refuses if the edit empties the file. Then `changed_lines()` in `workspace/diff.py` counts the changes and the `WorkingCopy` refuses if the total passes the diff limit. Only then does it write the file.
8. When the model calls `finish`, the Fix code calls `WorkingCopy.verify()`. It fails if the change is empty or over the diff limit. It also calls `check_parses()` in `workspace/syntax.py`, which fails if a changed file does not parse.
9. The Fix code calls `ensure_no_secret()` in `fix/secret_check.py`. This function uses `find_new_secret()` in `secrets/scan.py`. It looks only at text that the edit added. A Secret that was in the file before does not count.
10. `redact()` in `secrets/redact.py` replaces each credential value and each known secret pattern with `[redacted]`. The `Context.redact()` method calls it on every text that leaves the Engine.

Part 02 covers the run and the Fix. It calls the `Toolbox`, `WorkingCopy.verify()` and the secret scan. Part 04 covers the models, the interfaces, the errors and the constants files.

## Files

### tools/definitions.py

This file builds the list of tools that the model sees. It is its own file so that the descriptions and argument shapes live in one place.

* `tool_definitions()` — builds one `ToolDefinition` for each tool. A `ToolDefinition` is a checked record with a name, a description and a parameter schema. It takes no input. It returns a list. The first four items are the tools of the `TOOLS` table. The last item is `finish`, which uses `FinishArgs`. The description of each tool comes from `TOOL_DESCRIPTIONS`. The parameter schema comes from the argument model of the tool. `fix/conversation.py` calls it.

### tools/toolbox.py

This file holds the table of tools and the class that runs them. It is its own file so that one place decides how a tool call becomes text.

* `Handler` — a name for the type of a handler. A handler takes the checked arguments, a `WorkingCopy` and the `Settings`, and returns text.
* `TOOLS` — a table. It maps each tool name to a pair: the argument model and the handler. The names are `edit_file`, `read_file`, `search` and `list_dir`. `finish` is not in this table.
* `Toolbox` — the class that runs tool calls for the model. Its documentation says that each tool returns text and no tool raises an error.
* `Toolbox.__init__(working_copy, settings)` — stores the `WorkingCopy` and the `Settings`. `fix/attempt.py` creates the `Toolbox`.
* `Toolbox.run(call)` — runs one tool call. It takes a `ToolCall`. It returns text for the model. It returns `Error: The tool ... does not exist.` for an unknown name. It returns an error text for arguments that fail the check. Otherwise it runs the handler and cuts the result to `tool_result_max_bytes`. `fix/conversation.py` calls it.
* `_first_problem(error)` — turns a validation error into one short sentence. It takes the first problem only. It names the field and gives the message. It returns text such as `Field path: ...`. `Toolbox.run()` calls it.

### tools/result_cap.py

This file cuts a tool result that is too long. It is its own file so that all handlers get the same cut.

* `cap_result(text, limit)` — keeps the text if it is within `limit` bytes. If it is longer, it cuts the text and adds `NARROW_NOTE` on a new line. The note and the cut text together stay within `limit`. It takes the text and the limit in bytes. It returns text. A cut in the middle of a character drops that character. `Toolbox.run()` calls it.

### tools/handlers/readable.py

This file decides which files the model may read. Three handlers share it, so it is its own file.

* `readable_path(path, settings)` — checks that one path is readable. It passes the path and the extra refused patterns of the settings to `check_readable()`. It returns the cleaned path. It raises `RuleViolation` for a refused path. `read_file()` calls it.
* `readable_files(working_copy, settings)` — lists the files that the model may read. It goes through all files of the `WorkingCopy` and skips each refused file. It returns a list of paths. `list_dir()` and `search()` call it.

### tools/handlers/read_file.py

This file is the `read_file` tool. It gives the model the lines of one file.

* `read_file(args, working_copy, settings)` — reads a file from the `WorkingCopy`. The `WorkingCopy` gives the file as the model edited it so far. It starts at `start_line`, which is 1 by default, and gives at most `read_file_max_lines` lines. The default is 300. If lines remain, it adds `NARROW_NOTE`. It returns `Refused: ...` for a refused path. It returns `Error: ... is not a text file in the repository.` if the file is missing, is a folder, or is not text. `Toolbox.run()` calls it through the `TOOLS` table.

### tools/handlers/search.py

This file is the `search` tool. It finds lines that match a pattern.

* `search(args, working_copy, settings)` — compiles the pattern as a regular expression. A regular expression is a pattern language for text. It looks at each readable file, line by line. It skips files that are not text. It returns one line for each match, in the form `path:number:line`. It stops at `search_max_matches` matches. The default is 50. Then it adds `NARROW_NOTE`. It returns `No matches.` if nothing matches. It returns an error text if the pattern is not valid. `Toolbox.run()` calls it.

### tools/handlers/list_dir.py

This file is the `list_dir` tool. It shows what is in one folder.

* `list_dir(args, working_copy, settings)` — lists the readable files and folders directly inside a folder. The default folder is `.`, which is the repository root. A folder name ends with `/`. The Engine sorts the names. It returns `The folder has no files.` if nothing is there. It returns `Refused: ...` if the path is outside the repository. A refused file does not appear in the list. `Toolbox.run()` calls it.

### tools/handlers/edit_file.py

This file is the `edit_file` tool. It hands the edit to the `WorkingCopy` and turns the result into text.

* `edit_file(args, working_copy, settings)` — asks the `WorkingCopy` to replace the first match of `old` with `new` in `path`. It returns `Edit applied.` on success. If the `WorkingCopy` raises `EditRejected`, it returns the message of that error. `Toolbox.run()` calls it.

### workspace/path_rules.py

This file holds the safety rules for paths. Its first line says that these rules are code and not settings. A setting cannot turn them off.

* `normalize_dir(path)` — turns a folder path into a clean path. It changes `\` to `/` and takes out `.` and `..` parts that stay inside. The repository root becomes an empty string. It raises `RuleViolation` for an absolute path or a path that starts with `..`. `list_dir()` and `normalize_file()` call it.
* `normalize_file(path)` — turns a file path into a clean path. It uses `normalize_dir()`. It raises `RuleViolation` if the path is the repository root. `check_readable()` calls it.
* `check_readable(path, extra_patterns)` — refuses a file that may hold Secrets. It compares in lower case. It refuses any path with a `.git` part. It refuses a file name that matches `.env*`, `*.pem`, `*.key`, `*.p12`, `id_rsa*` or `.npmrc`. The extra patterns from the settings add to this list. It returns the clean path. Otherwise it raises `RuleViolation` with `This file may hold secrets.` `readable_path()`, `check_editable()` and `fix/attempt.py` call it.
* `check_editable(path, extra_patterns)` — refuses a file that the model may not change. It first runs `check_readable()`. It refuses a path inside `.github/workflows`. It refuses a lockfile, for example `uv.lock` or `package-lock.json`. It returns the clean path. Otherwise it raises `RuleViolation`. `WorkingCopy.edit()` calls it.

### workspace/diff.py

This file counts how many lines an edit changes. It exists so that the diff limit uses one count in both places that check it.

* `changed_lines(originals, currents)` — counts the changed lines of all edited files. It takes two tables that map a path to text: the text before the first edit and the text now. It adds up the count for each file. It returns a number. `WorkingCopy.edit()` and `WorkingCopy.verify()` call it.
* `_file_changed_lines(before, after)` — counts the changed lines of one file. It compares the two texts line by line. For each block of change it counts the larger of the old and new line counts. A change to a line ending or to a space counts as a change. It returns a number. `changed_lines()` calls it.

### workspace/working_copy.py

This file is the gate for edits. The `WorkingCopy` sits between the model and the `Workspace`. A `Workspace` is the part that reads and writes the real files. The `WorkingCopy` is its own file so that no edit can reach the files without the checks.

* `WorkingCopy` — applies edits to a `Workspace`. Its documentation says that each check runs before the Engine writes anything. It remembers the first text and the current text of each edited file.
* `WorkingCopy.__init__(workspace, settings)` — stores the `Workspace` and the `Settings`. It starts with no edited files.
* `WorkingCopy.read(path)` — returns the text of a file. It returns the edited text if the model edited the file. Otherwise it reads the file from the `Workspace`. Handlers and `edit()` call it.
* `WorkingCopy.list_files()` — returns the list of file paths from the `Workspace`. `readable_files()` calls it.
* `WorkingCopy.edit(path, old, new)` — replaces the first match of `old` with `new` in one file. It refuses the edit and raises `EditRejected` in these cases, in this order. The path breaks a path rule. The path is not an existing file, because new files are not allowed. The old text is not in the file. The edit would empty a file that had content. The total change would pass the diff limit. If all checks pass, it writes the file and remembers the new text.
* `WorkingCopy.edits()` — returns the old text and the new text of each file that the attempt edited. It returns a list of pairs. `fix/secret_check.py` calls it.
* `WorkingCopy.verify()` — runs the checks at `finish`. It raises `AttemptFailed` if the change is empty. It raises `AttemptFailed` if the change passes the diff limit. Then it calls `check_parses()`. `fix/attempt.py` calls it.

### workspace/syntax.py

This file checks that edited files still parse. To parse is to read text by the rules of a file type. A file that does not parse is broken. The file is separate so that a new file type needs a change in one place only.

* `PARSERS` — a table that maps a file suffix to a parser. `.py` uses the Python parser. `.json` uses the JSON parser. `.toml` uses the TOML parser.
* `check_parses(files)` — checks each file in a table of path and text. It chooses the parser from the file suffix. It skips a file of any other type. It raises `AttemptFailed` for the first file that does not parse. The message holds the path and the parser message. `WorkingCopy.verify()` calls it.

### secrets/scan.py

This file finds Secrets in text. It does not change text. It exists apart from `redact.py` because the scan answers a question and the redaction rewrites text.

* `_secrets_in(text, values)` — finds every Secret in a text. It looks for each credential value of the run and for each known secret pattern. It returns a list of pairs. Each pair holds the kind of the Secret and the text that matched. `find_secret()` and `find_new_secret()` call it.
* `find_secret(text, values)` — returns the kind of the first Secret in a text, or `None`. The answer never holds the Secret itself, so it is safe to put in a comment. `fix/secret_check.py` calls it on the commit message and on the explanation.
* `find_new_secret(before, after, values)` — returns the kind of the first Secret that the new text holds more often than the old text. It counts each matched text in both versions and subtracts. A Secret that was in the old text does not count. `fix/secret_check.py` calls it for each edited file.

### secrets/redact.py

This file hides Secrets in text. It exists so that one function protects every text that leaves the Engine.

* `redact(text, values)` — replaces each credential value and each text that matches a secret pattern with `[redacted]`. Two matches that overlap become one `[redacted]`. So no part of a Secret stays. It takes the text and the credential values. It returns the new text. `Context.redact()` and the run report call it.
* `_spans(text, values)` — finds where the Secrets are. It returns a list of start and end positions. It finds every place of each credential value, also where two places overlap. It also finds each match of each secret pattern. It skips empty credential values. `redact()` calls it.
* `_merged(spans)` — joins positions that overlap into one. It sorts the positions first. It returns a list of start and end positions. `redact()` calls it.

## Things to know

* The path rules are code. The settings can add refused read patterns through `extra_refused_read_patterns`. The settings cannot remove the built-in patterns.
* The Engine never makes a file and never removes one. `WorkingCopy.edit()` refuses a path that is not an existing file. It also refuses an edit that leaves a file with only white space.
* The diff limit is 200 changed lines by default. `WorkingCopy.edit()` checks it on every edit and `WorkingCopy.verify()` checks it again at `finish`. The count covers all edited files together.
* `check_parses()` knows only `.py`, `.json` and `.toml`. A broken file of another type, for example YAML, passes this check.
* The secret scan looks at the added text only. A Fix that edits near an old key does not fail. The scan reports the kind of the Secret and never the value.
* The default limits for tool results are 8192 bytes, 300 lines for `read_file` and 50 matches for `search`. The settings can change them. `tool_result_max_bytes` cannot be below 256.
* `Toolbox.run()` does not call `redact()` on tool results. The protection for read results is the refused-file rules in `check_readable()`. A Secret in a file that the rules permit can reach the model.
