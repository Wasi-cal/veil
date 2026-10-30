# The GitHub App in the service

**Status: deferred.** veil runs on one repo through the GitHub Action now. GR-26. The service code was removed. The GitHub App code was removed too. The Action uses the `GITHUB_TOKEN` of the workflow (ADR 0016). The commit `0bcf11c` has the App code. The part about `TokenExpired` stays in use.

The org-wide service acts on repos as a GitHub App (ticket GR-26, decision GR-5). The code is in `veil/adapters/github/` and `veil/shells/service/`. The Engine does not know the App.

## What we decided

- **The App has three permissions.** These are Contents write, Pull requests write and Metadata read. It has no Workflows permission, no Administration permission and no organization permission. `GitHubAppTokenSource.read_app()` reads the App and refuses it if its permissions differ in any way. It also refuses an App that listens to events. A worker calls it at start.
- **The webhook stays off.** GitHub does not report the state of the webhook through its API. So the check of the events is the nearest check. The App must listen to no events. The setup steps in this ADR turn the webhook off.
- **One token for each repo.** `mint(repo)` works as in ADR 0013. `run_repo` calls it inside the activity. The token is never an input or a result. Nothing keeps a token.
- **The list of repos.** `eligible_repos` takes the repos of the installation. It keeps the repos in `repos_allow`, if that list is not empty. It removes the repos in `repos_deny`. A name matches whatever the case. The installation limits the list. A name in `repos_allow` that is not in the installation never runs. The list of the installation comes from `RepoListCache`.
- **The token for the list.** `list_repos` mints a token for the installation. The token reads metadata only. The adapter refuses a token that holds more. The token goes to the list call and then goes away.
- **An expired token stops the repo.** GitHub answers 401 to a token that expired or that somebody revoked. Git prints a login error. Both become `TokenExpired`, a kind of `RepoProviderError`. The Engine stops the run when it sees this error, wherever it comes from. It publishes nothing, because it cannot. It leaves every ticket without an outcome for the next run. It sets `RunReport.stopped` to `token_expired`. The activity does not retry this error, because the next run mints a new token.
- **The bot identity.** `read_app()` reads the slug of the App and then the user ID of its bot. The author is `<slug>[bot]` with the email `<id>+<slug>[bot]@users.noreply.github.com`. The email never changes, and GitHub shows the App on the commit. `ServiceDependencies.author` has no default. A run cannot commit with the default author by mistake. The GitHub Action keeps its fixed author.

## What we accept for now

- The key is a plain key from a secret. The user chose to work locally first. So the criterion "the key service holds the key and the service cannot export it" is **not met**. A signer for the key service of the cloud is a later ticket. It needs a seam for the signature, with the plain key and the key service as the two adapters.
- No worker program calls `read_app` or `eligible_repos` yet. GR-29 does. Until then the author in the dependencies is the one that the caller gives.
- The audit of the events is not a proof that the webhook is off.
- The adapter finds a git login error in the text that git prints. A new wording of git can make the check miss. Then the error is a plain `RepoProviderError`, and the activity retries it.
- If the token expires before the Engine publishes a Fix that passed, the Fix is lost. The next run makes it again.
- A branch that the Engine pushed before the PR call failed stays on GitHub. This is true for any failure of the PR call, not only for an expiry. The next run does not find the branch, because the search starts from PRs.
- A list of more than 50 pages of 100 repos is a fault. The adapter refuses it.
- `GitHubAppTokenSource` now mints tokens, finds installations, lists repos and reads the App. It is the one client of the App on GitHub. A split comes if it grows.
- The report holds the stop reason. No alert reads it yet.

## Setup of the App (a person does this once)

1. Create the App in the organization. Turn the webhook off. Give it the three permissions and no event.
2. Install it on selected repos only.
3. Give `GOZU_APP_ID` and the private key to the service as secrets.
