# Check the default branch

The owner of the project decided this on 2026-11-03. Before this ADR the rule "never touch the default branch" was only a promise in the docs and in docstrings. No code looked up the name of the default branch.

## What we decided

- **The repo provider asks GitHub for the default branch.** The call is `GET /repos/{owner}/{repo}`, and the answer is the field `default_branch`. The provider asks once for each repo and keeps the answer for the run.
- **It checks before it pushes.** In `open_pr`, the provider refuses a PR if the Fix branch or the base branch is the default branch. The refusal comes before the push, so nothing reaches GitHub.
- **The older checks stay.** The Fix branch must start with the branch prefix. It may not equal the base. veil never forces a push and pushes one named branch only.
- **A bad answer is an error.** If GitHub gives no name, the provider raises an error and does not push.

## What this costs

- **One more call to GitHub** for each repo in a run. The token of the workflow already has the access for it.
- **A refusal stops the run.** The error is a `RepoProviderError`. Nothing catches it, so the run ends with exit 1 and the later groups do not run. This can happen only if a ticket has the default branch as its Source PR branch. A ticket like that is normally skipped before this point, because the default branch has no open PR of its own (`source_pr_not_open`).
- **Only the stub tests ran this call.** No real GitHub answered it.
