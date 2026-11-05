# No run on a Fix branch, and no second Fix after a merge

The owner of the project decided this on 2026-11-04. A test repo showed the problem.

## What happened

The workflow ran on `pull_request` with the type `synchronize`. A person merged a Fix PR into the Source PR branch. The push started a new run. The ticket was still open, and veil did not know that its Fix PR was merged. So veil made a second Fix PR for the same ticket. The person merged it, and the cycle went on. Each cycle used model tokens, and the Fixes got less useful each time.

## What we decided

- **A merged Fix PR means the ticket is skipped.** The repo provider reports `merged_pr` when a merged PR meets three conditions. It carries the issue label. It starts from a Fix branch of veil. Its base is the Source PR branch. The reason in the report is `merged_pr`. An open PR still wins over a merged PR, and a merged PR wins over a leftover Fix branch.
- **A run never starts on a Fix branch.** The Action checks the branch before it reads a credential, a ticket or a repo.
  - For a `pull_request` event, the branch is the head branch of the PR.
  - For any other event, the branch is `GITHUB_REF_NAME`.
  - A Fix branch starts with `veil/fix-`, with `gozu/fix-` or with the setting `branch_prefix`. The fixed prefixes always count. `gozu/fix-` is the prefix from before the rename, and it stays so that an older Fix branch is still safe.
  - The run ends with a notice and exit 0.
- **The ticket rule stays.** A ticket raised against a Fix branch is still skipped (`raised_against_fix_branch`). The new rule is about the run, and the old rule is about the ticket.
- **The example workflow has a guard.** The job does not start on a Fix branch. This saves the minutes of the runner. The check in the Action is the second layer.

## What this costs

- **A merged Fix that did not solve the finding is not tried again.** A person must close the ticket, or Gozu must make a new one. This is the same as for any ticket whose Fix PR is merged.
- **Nothing closes the ticket.** veil still never moves a ticket to Done. A scan or a person does it.
- **`synchronize` still starts a run for each push.** The run now finds no ticket to fix after a merge, so it costs few tokens. It still costs a job start. Do not use `synchronize` unless you need it.
