# Settings schema, layers and validation

Every number and every name that the Engine uses is a setting (ticket GR-21). One schema serves both Shells. This ADR follows the decisions in GR-3 and GR-11.

## What we decided

- **One declaration for each setting.** The `Settings` model declares each setting once. The declaration holds the type, the default, the minimum, the maximum, the rule for a repo and the reader. The checks and the catalog both come from it. So they cannot drift.
- **Four layers.** The order is defaults in code, org settings, repo settings, per-run overrides. A later layer wins. A layer changes only the settings that it names. A map, such as the severity map, changes only its own words.
- **A pure function.** `resolve_settings(org, repo, overrides)` merges the layers. It reads no file and no environment. A Shell passes plain mappings. It raises `SettingsError` before the Engine touches any ticket.
- **Clear messages.** The error lists every problem of every layer, one on each line. A line names the layer and the setting and says what is wrong. It never repeats a value, so a secret cannot reach a log. It does not repeat a key that is long, is not text or looks like a secret either.
- **What fails.** These all fail: an unknown key, a value of the wrong type and a value outside the bounds. A value that is too long fails, and so does a value that looks like a secret. Two spellings of one severity word in one layer fail too. A repo value that loosens an org value fails too. The name of a safety rule is an unknown key. The safety rules are code.
- **A repo can only tighten.** Each setting has one rule for a repo. `lower`: a repo may lower the value. `add_only`: a repo may add entries. `raise_only`: a repo may raise a severity bucket. `disable_only`: a repo may turn the setting off. `locked`: a repo may not change the value. `free`: a repo may set any value inside the bounds. A repo may choose its own model names and labels. This is a choice of the team.
- **Where the rule applies.** A rule applies only when the org layer set the value. With no org value, a repo may set any value inside the bounds. A per-run override is for an operator. It is not held to the org value.
- **No secrets.** Every layer refuses a value that matches a secret pattern. The message names the kind of secret and never the text. The `Settings` model refuses such a value too, so a caller that builds `Settings` by hand cannot skip the check. The layers and the rule for a repo exist only in `resolve_settings`.
- **YAML at the edge.** `load_settings_file` in `veil/adapters/` reads the repo file with PyYAML. It uses a safe loader, so a file cannot run code. It refuses aliases, because an alias can grow a small file into a huge value. It refuses a path that is a directory and a file that nests too deep. It also refuses a key that appears twice, a key that is not text and a file that is too big. It refuses a file that is not a mapping too. A missing or empty file gives no settings. The message never repeats the content of the file.
- **Bounds on size.** A name is at most 100 characters and an address at most 300. A list holds at most 200 entries of at most 200 characters.
- **The Jira site.** The setting `jira_site_url` must be an https address with no user name and no password in it.
- **Names are settings.** The label of a Failed Fix (`failed_fix_label`), the review status (`in_review_status`) and the eligible label (`eligible_label`) are settings. The Engine reads the first two. The Jira adapter reads the third. `JiraSettings.from_settings` builds the Jira settings from the settings of the run. The old status map of the Jira adapter is gone. A workflow that names the status another way changes `in_review_status`. The prefix `issue-` stays a constant. It is the contract with Gozu and not a name of this agent.
- **Attempts.** The setting `max_attempts` is 1 or 2. With 1, the Engine tries the cheap model only.
- **The full catalog.** The schema holds every setting of GR-2 to GR-11. This includes the values that only a Shell reads. They are the quiet window, the run limit, the heartbeat, the concurrent runs and the sweep of old checkouts. They are also the triggers, the repo lists, the Jira site, the project keys and the cache lifetimes. GR-23 to GR-25 read them. The catalog marks the reader of each setting.
- **The catalog file.** `docs/settings-catalog.md` has one row for each setting: key, default, minimum, maximum, rule for a repo, reader and cache lifetime. `python docs/settings/build.py` writes it. A test fails if the file is old. The cache lifetime of every row is the setting `cache_settings_ttl_seconds`, because Redis caches the whole snapshot of the settings.
- **Safe low defaults.** The cheap model is `gpt-6-luna`. The strong model is `gpt-6.1-terra`, a mid-tier model and not the flagship. These names come from the models page of OpenAI. The token ceiling is 100,000 for each run. The model-call rate is 20 for each minute. The schedule trigger is off.
- **The rate limit is a setting only.** The shared Redis counter enforces it (GR-11, GR-23). The Engine does not throttle.

## What we accept for now

- A service must not take `jira_site_url` from a repo file. With no org value, a repo file can set it, and the Jira credentials would go to that address. The service Shell must read the site from the org layer (GR-25). In the Action, the repo owner owns the credentials too.
- The Shell-only settings have no reader yet. A typo in them is caught, but nothing uses them until GR-23 to GR-25.
- A repo may choose a more costly model than the org uses. The org can lock the model names later by changing their rule.
- A per-run override can loosen an org value. Only an operator gives overrides.
- The bounds sit in the model, next to each setting, and not in `constants/`. The defaults are in `constants/`.
- The checks look at one setting at a time. Nothing checks that the strong model differs from the cheap model.
- The settings catalog says that all rows share one cache lifetime. A Shell may cache rows apart later.
- The sources of the org layer (the database, ADR GR-11) and the per-run snapshot are the work of the service Shell.
- The tracker status `To Do` is not a setting. The Engine never sets it. The tracker type and the parse check of GR-3 are not settings either. Jira is the only tracker, and the Engine always runs the parse check.
- The schema takes a text such as `25` for a number, because an override from an environment variable is text. A stricter check is a later choice.
- No Action run loaded a real repo file yet. The loader has tests with real files only.
