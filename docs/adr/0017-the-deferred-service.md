# The deferred org-wide service

veil runs on one repo through the GitHub Action (ADR 0016). We built an org-wide service first, then deleted it. This note keeps the decisions that matter if the service comes back. It replaces four ADRs: 0011 (PostgreSQL), 0012 (Redis), 0014 (Temporal) and 0015 (GitHub App).

All the code is in git. Run `git show 0bcf11c --stat` to see it. The commit `ebc44ab` deleted it. The tickets were GR-22, GR-23, GR-25 and GR-26.

## What the service was

One Engine runs for one repo inside a Temporal workflow. The workflow ID comes from the repo name, so a second start joins the active run. A second Shell calls the same Engine (ADR 0001).

## Decisions to keep

- **Temporal.** One workflow for each repo. Two activities: `read_settings` and `run_engine`. The Engine is not split into one activity for each ticket. The Engine has an optional `progress` callback, and the activity turns it into a heartbeat that carries the tokens used.
- **Retry.** Only an infrastructure failure retries, at most twice. A Failed Fix is a normal result and never retries. A retry reads the last heartbeat and lowers the token ceiling by the tokens already used. It uses the same settings snapshot.
- **No credential in Temporal.** The activity mints the GitHub token and keeps it. A test read the whole workflow history and found no credential.
- **Temporal is easy to delete.** Only one folder imported `temporalio`. The work of a run was one function with no runner in it.
- **PostgreSQL settings store.** One `settings` table for the org layer and the repo layer. The table itself refused wrong types, values outside the bounds and secrets. Every write had an actor and wrote an audit row. A snapshot was plain data, so a retry saw the same values.
- **Redis cache.** It held only the settings snapshot, the Jira metadata, the repo list and the shared model-call counters. It never held a token or a key. A Redis outage was a cache miss, never a failed run.
- **GitHub App.** Three permissions: Contents write, Pull requests write and Metadata read. No Workflows or Administration permission and no webhook events. One token for each repo, minted inside the activity, never an input or a result.
- **The repo list.** The repos of the installation, narrowed by an allow list and a deny list. The installation limits the list.
- **The bot identity.** The author was `<slug>[bot]` with the email `<id>+<slug>[bot]@users.noreply.github.com`.

## Not finished when we stopped

- The key was a plain key from a secret. A cloud key service that cannot export the key was not built. It needs a seam for the signature, with two adapters.
- No worker program existed (GR-29), and no trigger code (webhook, schedule, quiet window: GR-27).
- Nothing wired a concurrency limit or a shared model-call limit (GR-28).
- No test ran against a real Temporal cluster, a real PostgreSQL or Redis on AWS, or a real GitHub App.

## What stayed in veil

- `TokenExpired` and the Engine stop (ADR 0016).
- The bounded retry of one model call in the OpenAI client (ADR 0009).
- `RepoScopedTracker`, `ServiceUrls`, `RunCredentials` and `build_context`, in `veil/shells/shared/`.
