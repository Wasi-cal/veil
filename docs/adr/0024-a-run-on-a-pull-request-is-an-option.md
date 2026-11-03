# A run on a pull request is an option

The owner of the project decided this on 2026-11-03. It changes ADR 0013, which allowed three events only.

## What we decided

- **A new trigger.** The event `pull_request` may start a run. The setting `pull_request_enabled` turns it on. The default is off.
- **A fork never runs.** The Action reads the event file of the runner (`GITHUB_EVENT_PATH`). It takes two fields: the head branch and the repo that holds it. If the repo is not this repo, or the repo is gone, the run ends with a notice and exit 0. This happens before the Action reads a credential, a ticket or a repo.
- **A bad event file stops the run.** A missing file, a file that is not JSON and a file without the head give exit 1 and one error line.
- **A run sees the tickets of one branch.** For a `pull_request` run, the tracker shows the Engine only the tickets whose branch is the head branch of the PR. The repo scope stays. Other events see the tickets of every branch, as before.
- **`pull_request_target` stays refused.** It gives secrets to code from a fork.
- **The example workflow keeps the trigger as a comment.** A person must add it and turn on the setting.

## What this costs

- **The tickets may not exist yet.** Gozu writes the tickets after it scans the PR. A run on the event `opened` can start before that. The run then finds nothing. The next event, a schedule or a `repository_dispatch` from Gozu, finds the tickets.
- **A run for each event.** With the default types, a person who opens or reopens a PR starts a run. The concurrency group of the example workflow queues the runs. Do not add the type `synchronize` unless you want a run for each push.
- **A bot PR can fail.** A PR from Dependabot gets no secrets and a read-only token. The run stops with an error about a missing credential.
- **The token needs write access.** A PR from this repo gets the permissions of the `permissions` block. A repo setting that makes the token read-only for PRs stops the push.
