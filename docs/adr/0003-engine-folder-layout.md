# Engine folder layout

The `engine` package has one folder for each concern. A folder imports only from the folders below it in this list:

1. `run.py` loops over the Gozu Tickets.
2. `fix/` and `eligibility/` sit side by side. `fix/` makes one attempt to fix one ticket: the first prompt, the model conversation with the step cap, the publish step and the Failed Fix record. `eligibility/` decides which Gozu Tickets the Engine may fix: the no-loop rule, the Failed Fix marker, the issue label and the check for an existing Fix.
3. `tools/` holds the tools that the model calls. Each tool has its own file in `tools/handlers/`.
4. `context.py` holds what the caller passes in.
5. `workspace/` applies edits safely: path rules, the changed-line count and the syntax check.
6. `interfaces/` holds the tracker, the repo provider, the workspace and the model client.
7. `models/` holds the pydantic models, one folder for each purpose.
8. `errors/` and `constants/` hold the exception types and the fixed values.

We chose this so that a file has one reason to change and a reader can find code by its concern. The `fix` and `eligibility` folders do not import each other. The `tools` and `context` folders do not import each other. The `errors` and `constants` folders do not import each other.

A contract in `pyproject.toml` enforces the order. The tests mirror the concerns: `flow`, `eligibility`, `source_pr`, `escalation`, `budget`, `limits`, `edits`, `reads`, `failures` and `settings`.
