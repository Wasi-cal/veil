# The GitHub Action Shell

The Action runs the Engine on one repo from a GitHub workflow (ticket GR-24, decisions GR-6 and GR-7). The code is in `veil/shells/github_action/`. The Engine does not change.

## What we decided

- **One container Action.** `action.yml` points at a prebuilt image. There is no JavaScript variant and no composite variant. The `Dockerfile` installs the dependencies and git at build time. Nothing installs at run time. GR-29 builds and publishes the image.
- **The order of a run.** `run_action(environ)` does every check that needs no token first. It reads the runner variables, loads the repo settings, checks the event and reads the credentials. Then it masks the credentials, mints the GitHub token and masks it. Then it builds the context, runs the Engine once and writes the summary. A `finally` step closes the checkouts.
- **One GitHub credential.** The Action mints a GitHub App installation token from `GOZU_APP_ID` and `GOZU_APP_PRIVATE_KEY`. There is no PAT and no `GITHUB_TOKEN` fallback. A test shows that a `GITHUB_TOKEN` variable does nothing.
- **The token check.** `GitHubAppTokenSource` signs a JWT with PyJWT, finds the installation of the repo and asks for a token for that repo alone. It refuses the reply unless the reply covers exactly that repo. It also refuses the reply unless the permissions are contents write and pull requests write. GitHub adds metadata read. Any other permission, for example `workflows`, fails the check. The error never repeats the key, the JWT or the token.
- **Any failure stops the run.** The Action prints one `::error::` line and exits with 1. At that point the Action did not touch any ticket or repo. A Failed Fix is a normal result. It does not fail the run.
- **Own repo only.** `OwnRepoTracker` wraps the Jira tracker. The Engine sees only the tickets of the repo of the workflow. A ticket of another repo never reaches the Engine, because the token covers one repo.
- **Masking.** The Action prints `::add-mask::` for the Jira token, the OpenAI key, the App key and the GitHub token before it uses them. It masks a value with many lines one line at a time. It escapes `%`, as the runner needs. Every failure line goes through `redact` with the credential values of the run. The Action also sends a crash that is not a known error through `redact`.
- **Where the token goes.** The token goes to the repo provider and its API client only. The repo provider gives it to git through a header for one command (ADR 0007). The Jira token goes to the tracker and the OpenAI key goes to the model client.
- **Credential variables are settings.** `jira_email_env`, `jira_token_env` and `openai_key_env` name the variables. The defaults are `JIRA_EMAIL`, `JIRA_API_TOKEN` and `OPENAI_API_KEY`. A new migration, 0004, seeds their org rows (ADR 0011). A name must be capital letters, digits and underscores. A name may not start with `GITHUB_`, `ACTIONS_`, `RUNNER_`, `INPUT_` or `GOZU_`. So a repo file cannot send the App key to Jira. Two credentials may not share one variable. A missing, empty or short value stops the run. The message names the variable and never shows a value. A missing email means a bearer token.
- **Events and triggers.** `schedule` runs only if `schedule_enabled` is on. `workflow_dispatch` needs `on_demand_enabled`. `repository_dispatch` needs `event_enabled`. An event that is off ends the run with a notice and exit 0. It mints no token. Any other event, for example `pull_request`, fails. The Action never runs on a fork pull request.
- **Settings.** The Action loads `.gozu/jira-to-pr.yml` from the workspace and resolves it as the repo layer. It has no org layer and no per-run overrides. The workflow runs `actions/checkout` first, with `persist-credentials: false`.
- **The example workflow.** `docs/examples/veil-action-workflow.yml` has the triggers `schedule` and `workflow_dispatch`. It has `repository_dispatch` as a comment. It grants `contents: write` and `pull-requests: write` and no other permission. It sets a concurrency group for each repo with `cancel-in-progress: false`. GitHub then keeps one waiting run, so an event during a run makes one follow-up run. It works on self-hosted runners.
- **The run report.** The Action appends the report to the step summary. It lists the Fix PRs, the outcome of each ticket, the skipped tickets and the tokens used.
- **A seam for tests.** `ServiceUrls` holds the addresses of GitHub, git and OpenAI. It can hold the Jira gateway address too. A test points them at stub servers and at a local git remote. A test can give a `TokenSource` and a replacement for `run`.

## What we accept for now

- No run used a real GitHub App, a real Jira site or a real OpenAI key. The tests use stubs and a local git remote.
- Nobody built the image. The Docker daemon was off. The name `ghcr.io/calfus/veil` in `action.yml` and in the example is a placeholder. GR-29 sets the real name, builds the image and tests it.
- The image holds only what the Action needs. The service code and its dependencies are removed.
- Only github.com works. GitHub Enterprise Server needs a setting for the API address and the git address.
- The base images of the `Dockerfile` have no pinned version, and the image runs as root. GR-29 pins them. The runner needs root for the workspace.
- A container Action needs Docker on the runner. A self-hosted runner must be Linux and must run Docker. The example workflow uses `ubuntu-latest`. A self-hosted runner needs another `runs-on` value.
- The App key is a repo secret and stays in the environment of the Action process. The model loop has no shell and the git child gets no such variable. But the process itself holds the key.
- A repo file can name any variable that the step sets and that is not reserved. A repo writer can choose which secret goes to Jira or to OpenAI. A repo writer can also choose the Jira site (ADR 0010).
- The token lives for one hour. If it expires during a run, the Engine stops the run, leaves the tickets without an outcome for the next run and reports `token_expired` (ADR 0015). There is no re-mint.
- The Action ignores `schedule_cron`. The cron lives in the workflow file.
- `workflow_dispatch` from a branch other than the default branch reads the settings of that branch. Protect the branches that can run the workflow.
- The check of the token trusts the reply of GitHub. It cannot see a permission that GitHub hides.
- A workflow command is only a request to the runner. The runner masks a value only when it sees it as exact text.
