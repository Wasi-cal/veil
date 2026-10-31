# One repo, the token of the workflow

veil runs on one repo through the GitHub Action. This ADR changes the GitHub credential of ADR 0013. It also removes the code that only the org-wide service used.

## What we decided

- **The Action uses the `GITHUB_TOKEN` of the workflow.** The workflow passes it in `env`. GitHub makes the token for each job. It covers this repo. It expires when the job ends. The `permissions` block of the workflow limits it to contents write and pull requests write. This replaces the GitHub App of ADR 0013. There is no PAT and no key to keep.
- **The GitHub App code is gone.** This covers the token source, the App check, the bot identity, the list of installation repos, PyJWT and its tests. The commit `0bcf11c` has them.
- **The service is gone.** This covers the service Shell, Temporal, PostgreSQL and Redis (ADRs 0011, 0012, 0014 and 0015 say deferred). The commit `0bcf11c` has them.
- **The settings of the service are gone.** The Action did not read them. They are: the model-call rate, the allow and deny lists of repos, the cron, the quiet window and the run time-out. The rest are the heartbeat, the number of concurrent runs, the checkout sweep and the cache lifetimes. The catalog has no cache column now.
- **What stays.** `TokenExpired` stays. The job token expires after one hour. If GitHub refuses it in the middle of a run, the Engine stops the run, leaves the tickets for the next run and reports `token_expired`.

- **The eligible label is optional.** An empty `eligible_label` turns the label check off. The default stays `veil-eligible`.
- **A ticket always has a branch.** No word stands for a missing branch. The tools that write tickets (Gozurion and the Gozu CLI) stop before they write one. They find the branch from the runner or from git, also on a detached HEAD. If they find none, they stop and write nothing. veil skips a ticket that has no branch.
- **The text that veil writes follows ASD-STE100.** The prompt tells the model to write the commit message and the three parts in Simplified Technical English. The three parts are the problem, the change and what it solves. The PR and the ticket comment show them under three labels. The Engine refuses a part that copies the text of the ticket. The Engine sends a sentence of more than 25 words back to the model. The PR title says "ticket" for one ticket.

## What we accept for now

- A PR that the `GITHUB_TOKEN` opens does not start other workflows. CI does not run on a Fix PR until a person pushes to it.
- Commits show the fixed author `Gozu Veil`. They do not show a bot of an App.
- A repo that needs to run CI on Fix PRs needs another token. That is a new decision.
- The settings layers (org, repo, overrides) and the tighten rules stay in the Engine. The Action uses the repo layer only. Removing the layers is a later cut.
- A failed PR call leaves the pushed Fix branch on GitHub. A plain rerun is then rejected, because the push is never forced. A person must remove the branch first. The next change must let a rerun reuse or reset the Fix branch of veil.
- The PR title is "Fix 1 tickets". The text is not grammatical for one ticket.

## The first trial

On 2026-10-31 the Action ran by hand on one public repo against one seeded ticket. The workflow built the image on the runner. The run opened a draft Fix PR with a working fix. The ticket moved to In Progress and got a comment. The record is in the ticket GR-30. The trial needed four changes outside the code. They were the `issue-` label, the exact branch name, an `in_review_status` that exists in the workflow, and the repo setting for PRs.
