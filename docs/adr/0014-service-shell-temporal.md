# The service Shell on Temporal

The org-wide service runs the Engine for one repo inside a Temporal workflow and activity (ticket GR-25, decision GR-9). The code is in `veil/shells/service/`. The code that both Shells use is in `veil/shells/shared/`. The Engine does not know Temporal.

## What we decided

- **One workflow for each repo.** `RepoRunWorkflow` has the ID `veil-run-<owner>--<name>`. `start_repo_run` starts it with the conflict policy "use existing". A second start for an active repo joins the first run and starts no second run.
- **Two activities.** `read_settings` reads the settings snapshot for the repo. The workflow keeps it in its history. `run_engine` gets the repo and the snapshot, runs the Engine once and returns the run report. The Engine is not split into one activity for each ticket.
- **The same settings on a retry.** The snapshot is part of the input of `run_engine`. A retry never reads the database again. A test changes a setting between two attempts and shows that the second attempt keeps the old value.
- **The limits are settings.** The workflow takes the time limit from `run_timeout_minutes` and the heartbeat time-out from `heartbeat_seconds`. The defaults are 60 minutes and 120 seconds. The activity has at most 2 attempts. This number is a constant. The setting `max_attempts` is another thing. It counts the attempts of the Engine to fix one ticket.
- **A heartbeat carries the tokens used.** The Engine has an optional `progress` callback in `Context`. It calls the callback with the tokens used so far, after each model call and after each ticket. The activity turns each call into a Temporal heartbeat. An error of the callback stops the run.
- **The budget belongs to the run.** An attempt reads the tokens of the last heartbeat. It lowers `token_ceiling` by that number. It adds the number to the tokens of the report. A ceiling of zero makes the Engine leave all tickets for the next run.
- **Which errors retry.** A `ModelClientError` with `retryable` set may retry. A `TrackerError` with no status, with 408, 429 or 500 and more may retry. A `RepoProviderError` may retry. Every other error does not retry. These are a settings error, a login error and a bug. A Failed Fix is a normal result. It never retries. The message of the error goes through `redact` before Temporal stores it.
- **No credential in Temporal.** `ServiceDependencies` holds the token source, the settings source and the credentials. A worker builds it at start. It is never an input or a result. The activity mints the GitHub token and keeps it. A test reads the whole workflow history, with every payload decoded. It finds no credential, also not in a failure message.
- **One repo for each run.** The Engine sees only the tickets of the repo of the workflow. `RepoScopedTracker` does this for both Shells.
- **Old checkouts.** When a worker starts, it reads the org settings. It deletes the directories in the checkout root that are older than `checkout_sweep_minutes`. It never follows a link and never deletes a plain file. The activity gives the checkout root to the repo provider, so the sweep finds them.
- **Shared Shell code.** `ServiceUrls`, `RunCredentials`, `RepoScopedTracker` and `build_context` moved to `veil/shells/shared/`. The GitHub Action and the service both use them. A rule checks that no Shell uses another Shell and that shared code uses no Shell.
- **The bounded retry of one model call.** `OpenAIModelClient` tries a call with `retryable` set again at most twice. It waits 1 second, then 2 seconds, with a cap of 8 seconds. A rejected call costs no tokens. So the token ceiling stays true. A permanent error stops at once. This closes the gap of ADR 0009.
- **Temporal is easy to delete.** Only the folder `veil/shells/service/temporal/` imports `temporalio`. A contract in `pyproject.toml` checks this. The work of a run is `run_repo`. It has no runner in it. A test loads the core with `temporalio` blocked. To drop Temporal: delete the folder `temporal/` and its tests, delete the extra `service` and the dev dependency, and write another runner that calls `run_repo`. The runner decides when to retry. `RunFailed.retryable` tells it which failures may retry.
- **`temporalio` is optional.** It is in the extra `service` and in the dev group. The image of the Action does not carry it. The tests start a throwaway dev server from the `temporal` program of the machine, in the same way as for PostgreSQL and Redis. `VEIL_TEST_TEMPORAL_HOST` points at another server.

## What we accept for now

- No worker ran against a real Temporal cluster, real PostgreSQL on AWS or a real GitHub App. The tests use a dev server and stubs.
- The tests use the real clock of the dev server. A retry waits 1 second. No test proves the heartbeat time-out, because that needs time skipping.
- `GitHubAppTokenSource` mints the token with a key from a secret. The key service of the cloud is a later ticket (ADR 0015). The real worker program with its settings comes in GR-29. This ticket has no `main` for the worker.
- The workflow does not catch a bad snapshot. The store refuses bad rows, so a bad snapshot cannot come from it.
- A thread sends the heartbeat. A cancel of the workflow reaches the Engine only at the next heartbeat call. It does not stop a model call that is running.
- A retry after a crash repeats the model calls that ran before the last heartbeat. The budget holds only up to that heartbeat.
- A `RepoProviderError` retries even when it is permanent. The cost is one more attempt.
- Each attempt mints its own token. A test shows two mints across a real retry.
- A worker runs at most 16 activities at once. The setting `max_concurrent_runs` and the model-call limit are the work of GR-28.
- The sweep reads the age of a directory from its modified time. A checkout that a run still uses is far younger than the limit.
- The model retry has no jitter and does not read a `Retry-After` header.
- Only one run exists for a repo at one time. The quiet window, the signal-with-start and the schedule are the work of GR-27.
