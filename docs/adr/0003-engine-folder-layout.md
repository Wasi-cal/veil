# Engine folder layout

The `engine` package has one folder for each concern. A folder imports only from the folders below it in this list:

1. `run.py` loops over the Gozu Tickets.
2. `fix/`, `eligibility/` and `grouping/` sit side by side. `fix/` makes one attempt to fix one ticket. It holds the first prompt, the model conversation with the step cap, the PR text, the publish step and the Failed Fix record. `eligibility/` decides which Gozu Tickets the Engine may fix: the no-loop rule, the Failed Fix marker, the issue label and the check for an existing Fix. `grouping/` decides which tickets share a Fix PR.
3. `tools/` holds the tools that the model calls. Each tool has its own file in `tools/handlers/`.
4. `context.py` holds what the caller passes in.
5. `workspace/`, `secrets/` and `config/` sit side by side. `workspace/` applies edits safely: path rules, the changed-line count and the syntax check. `secrets/` finds secrets in a text and hides credential values. `config/` merges the layers of settings, checks them and writes the settings catalog.
6. `interfaces/` holds the tracker, the repo provider, the workspace and the model client.
7. `models/` holds the pydantic models, one folder for each purpose.
8. `errors/` and `constants/` hold the exception types and the fixed values.

We chose this so that a file has one reason to change and a reader can find code by its concern. The `fix`, `eligibility` and `grouping` folders do not import each other. The `tools` and `context` folders do not import each other. The `workspace`, `secrets` and `config` folders do not import each other. The `errors` and `constants` folders do not import each other.

A contract in `pyproject.toml` enforces the order. The tests mirror the concerns: `architecture`, `flow`, `secrets`, `grouping`, `eligibility`, `source_pr`, `escalation`, `budget`, `limits`, `edits`, `reads`, `failures` and `settings`.

## Where the constants live

Every fixed value lives in a `constants/` folder. A file in `constants/` holds one concern, for example `limits.py` or `secrets.py`. It imports nothing from the Engine, except the files in the same folder.

- **The Engine** has `engine/constants/`. The adapters may import from it.
- **An adapter** has its own `constants/` folder, for example `adapters/github/constants/`. The Engine must not import an adapter, so an adapter cannot use `engine/constants/` for its own values. A contract in `pyproject.toml` keeps the adapter constants at the bottom of the adapter.
- **Code that adapters share** has `adapters/constants/`. It holds the values that more than one adapter uses, for example the time-out.
- **A type that names a set of values**, such as `FixKind` or `PrState`, sits next to its values.
- **A registry stays in its module.** `TOOLS`, `PARSERS` and the HTTP opener of the GitHub adapter hold functions or objects that come from code. A constants folder cannot import that code.

A test in `tests/architecture` fails if a module outside a `constants/` folder defines an upper-case name. The registries are the only exceptions. A type variable such as `T = TypeVar("T")` is not a constant, so the test skips it.
