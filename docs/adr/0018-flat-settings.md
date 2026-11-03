# One flat settings file

The Action runs on one repo. So the settings come from one file, `.gozu/jira-to-pr.yml`. This ADR removes the layers of ADR 0010 that nothing used.

## What we decided

- **One flat model.** `Settings` is a pydantic model with a default, a type and a range for each setting. `parse_settings(values)` checks a mapping and returns the settings. No value means the defaults.
- **The layers are gone.** There is no org layer and there are no per-run overrides. The org layer needed a store, and we put the store off (ADR 0017).
- **The tighten rules are gone.** The rules `lower`, `add_only`, `raise_only`, `disable_only` and `locked` only worked when an org value existed. Without an org layer they did nothing.
- **The catalog is gone.** We removed the generator, the catalog entries and the generated file. `docs/settings.md` is a plain document. A test fails if a setting is missing from it.
- **Every safety check stays.** An unknown key fails, and so does a value of the wrong type, outside its range or too long. A value that looks like a secret fails, also in a list or in an address. The Jira site must be an https address with no password. The branch prefix must be safe. A message names the setting and never repeats a value. A message lists every problem at once.
- **The safety rules stay code.** A setting with the name of a safety rule is an unknown key.

## What we accept for now

- The repo file decides all settings, also the Jira site. A person who can change that file can send the Jira credentials to another https address (ADR 0010). Protect the branches that can run the workflow.
- A new setting needs a line in `docs/settings.md`. The test shows which one is missing.
- If an org layer comes back, the tighten rules come back with it. ADR 0017 and git history keep the old design.
