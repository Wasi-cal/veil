# How veil gets started: feasibility of two routes

Status: draft for discussion, 2026-11-04. Not an ADR. Nothing here is decided.

## The story

1. A dev pushes a branch.
2. Gozu scans it (Trivy and Semgrep, in GitHub Actions).
3. Gozu writes the findings as Jira tickets, in the same workflow.
4. veil fixes the tickets and opens a Fix PR into the source branch.
5. If the findings are above the threshold, the dev cannot merge. They merge the Fix PR, Gozu scans again, and the check passes.

The new Gozu workflow is planned separately. It has no S3, Lambda or Temporal step. This page covers how veil gets started after step 3.

## Rules for the choice

- Fix quality does not change. Both routes run the same Engine with the default settings (two attempts, strong model on the second, 100,000 token cap for each ticket). We save money on infrastructure, not on the Fix.
- A delay of minutes is fine if it saves money.
- GitHub only. No new always-on service.

Correction to earlier advice: setting `max_attempts: 1` or a low `ticket_token_cap` would lower the fix rate. Do not use them to save money.

## The handoff is simple now

Gozu's workflow creates the tickets itself. They exist when the scan job ends. So veil can run as the next job in the same workflow, with `needs:`. No dispatch, no token, no timer.

The veil job must still run when the scan job fails the threshold. That failing check is what blocks the merge. Give the veil job a condition that ignores a failed scan, for example `if: ${{ !cancelled() }}`. If the scan job crashes, no tickets exist and veil finds nothing, which is harmless.

## Route A: a veil job in the Gozu workflow, on the EC2 runner

```
push -> scan job (Trivy, Semgrep) -> Gozu writes Jira tickets -> veil job (needs: scan) -> Fix PR
        all jobs on the self-hosted EC2 runner
```

What to build:
- One `veil` job in the Gozu workflow, with `needs:` on the scan job and `runs-on: [self-hosted, linux, x64]`. It takes `permissions: contents: write, pull-requests: write`. It uses `actions/checkout` with `persist-credentials: false`, then `Wasi-cal/veil@v1`. The example is `docs/examples/veil-action-workflow.yml`.
- Secrets: `JIRA_EMAIL`, `JIRA_API_TOKEN`, `OPENAI_API_KEY`.
- If the Gozu workflow is a reusable workflow, add the veil job once there and every repo that calls it gets veil.

Cost: the EC2 instance you already pay for, and OpenAI tokens. No new AWS service, no new secret to keep.

Effort: very small. One job.

Checks that must pass:
- Docker on the runner, and the runner user can use it.
- The instance is x86. The image is `linux/amd64` only. If it is Graviton, build a multi-arch image first.
- One runner runs one job at a time. Pushes from many devs queue. veil's `concurrency` group gives one run for each repo.
- Per ADR 0024, a run on `push` sees the tickets of every branch of the repo, not only the pushed one. With `pull_request` on, it sees only the PR's branch, but then the scan must run on the same event. Decide which one you want.
- Never turn on `pull_request` for a public repo on a self-hosted runner.
- GitHub announced a charge of $0.002 a minute for self-hosted runners on private repos, then postponed it in December 2025. I could not confirm today's status. Check the GitHub billing docs before we promise "free".

A Fix PR that veil pushes with `GITHUB_TOKEN` does not start other workflows. This is fine here: a person merges the Fix PR into the source branch, and that push starts the Gozu scan.

## Route B: serverless start with a GitHub App

```
push -> scan job -> tickets -> signal -> Lambda -> ECS Fargate task runs the veil image -> Fix PR
```

With the new Gozu workflow, Route B adds a hop that Route A does not need. The only reason to pick it is to keep veil off the EC2 runner and the repo workflows.

The signal can be:
- **A GitHub App webhook** on `workflow_run` completed. It needs no change in any repo.
- **A last step in the Gozu workflow** that calls the Lambda over HTTPS with a secret. It needs that step in the workflow.

What to build:
- A GitHub App with Contents write, Pull requests write and Metadata read. No Workflows permission.
- A Lambda that checks the signal, mints the installation token and starts the Fargate task. The token is made inside the task, never passed in an event.
- A new thin Shell for the container. It checks out the repo, builds the context and calls `run(context)`. `veil/shells/shared/` still has `build_context`, `RepoScopedTracker`, `ServiceUrls` and `RunCredentials`. The deleted service Shell (commit `0bcf11c`) is a reference.
- The App key in AWS Secrets Manager, and the three secrets of Route A.
- A lock so two tasks never run for one repo.

Cost: Fargate bills by the second, so a short run costs cents. The Lambda and Secrets Manager add very little. Use a public subnet with a public IP. A NAT gateway costs a fixed amount every month.

Checks that must pass:
- A Lambda cannot run the Engine. Its limit is 15 minutes. It must only start the work.
- The new Shell is new code and needs tests like the Action Shell has.
- Nothing here has been run on real AWS or a real GitHub App. The old service never was either (ADR 0017).

Effort: medium.

The old B1 (a Lambda that sends `repository_dispatch` to the runner) is gone. Route A needs no dispatch now, so B1 adds nothing.

## Side by side

| | A: veil job on EC2 | B: Lambda + Fargate |
|---|---|---|
| New code in veil | None | A new Shell |
| New AWS parts | None | Lambda, ECS task, Secrets Manager |
| New secret to keep | None | GitHub App key |
| Change in each repo | One job in the Gozu workflow, once if it is reusable | None with the App webhook |
| Compute cost | Existing EC2 | Cents for each run |
| Many devs at once | Queue on the runner | Each run is its own task |
| Start delay | Seconds after the scan | Seconds to a minute |
| Fix quality | Same Engine | Same Engine |
| Effort | Very small | Medium |

## Open questions

1. Is the EC2 instance x86, and does it carry other CI load? Graviton needs a multi-arch image. Shared load slows the queue.
2. Is the new Gozu workflow reusable? If yes, Route A needs the veil job in one place.
3. How does the scan job report the threshold? The veil job's condition depends on it.
4. Should veil run on every push, or only on a pull request? Per ADR 0024 this changes which tickets it sees.
5. Who owns a GitHub App for the org, and who may hold its key? Only Route B needs one.
6. What happens if two runs start for one repo? A has a concurrency group. B needs its own lock.

## Not verified

- GitHub's runner charge status (see above).
- Nothing in Route B has run on real AWS or a real GitHub App.
- I have not seen the new Gozu workflow.
- The ADR 0024 claim about push events seeing every branch comes from the docs, not from the code.
