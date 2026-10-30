# One repo, the token of the workflow

veil runs on one repo through the GitHub Action. This ADR changes the GitHub credential of ADR 0013. It also removes the code that only the org-wide service used.

## What we decided

- **The Action uses the `GITHUB_TOKEN` of the workflow.** The workflow passes it in `env`. GitHub makes the token for each job. It covers this repo. It expires when the job ends. The `permissions` block of the workflow limits it to contents write and pull requests write. This replaces the GitHub App of ADR 0013. There is no PAT and no key to keep.
- **The GitHub App code is gone.** This covers the token source, the App check, the bot identity, the list of installation repos, PyJWT and its tests. The commit `0bcf11c` has them.
- **The service is gone.** This covers the service Shell, Temporal, PostgreSQL and Redis (ADRs 0011, 0012, 0014 and 0015 say deferred). The commit `0bcf11c` has them.
- **The settings of the service are gone.** The Action did not read them. They are: the model-call rate, the allow and deny lists of repos, the cron, the quiet window and the run time-out. The rest are the heartbeat, the number of concurrent runs, the checkout sweep and the cache lifetimes. The catalog has no cache column now.
- **What stays.** `TokenExpired` stays. The job token expires after one hour. If GitHub refuses it in the middle of a run, the Engine stops the run, leaves the tickets for the next run and reports `token_expired`.

## What we accept for now

- A PR that the `GITHUB_TOKEN` opens does not start other workflows. CI does not run on a Fix PR until a person pushes to it.
- Commits show the fixed author `Gozu Veil`. They do not show a bot of an App.
- A repo that needs to run CI on Fix PRs needs another token. That is a new decision.
- The settings layers (org, repo, overrides) and the tighten rules stay in the Engine. The Action uses the repo layer only. Removing the layers is a later cut.
- No run used a real GitHub token, Jira site or OpenAI key.
