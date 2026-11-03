# One PR for each file

The owner of the project decided this on 2026-11-03. It changes ADR 0005.

## What we decided

- **No Shared PR.** The Engine puts no Low or Medium tickets together. There is no cap and no setting `shared_pr_max`.
- **One PR for each ticket.** A ticket gets its own PR, whatever its severity. One hundred tickets on one hundred files give one hundred PRs.
- **The same-file rule stays.** Tickets that flag the same file in the same Source PR share one PR, because their Fixes overlap. The body of the PR gives the reason. This now holds for every severity.
- **The order.** The Engine runs the PRs High first, then Medium, then Low. PRs of equal rank keep the order of the tickets. The severity map sets only this order.
- **The branch name.** It is the prefix and the key of the first Fix that passed. The word `shared` is gone.
- **The `.github/` folder is off limits.** The Engine does not read, list, search or edit any file in it, at any depth. The rule was `.github/workflows/` and edits only. It now covers workflows, CODEOWNERS, dependabot files and local actions. A ticket on a `.github` file is skipped with the reason `ignored_path`. A short step in this ADR allowed workflow edits. The owner reversed it on the same day.

## What this costs

- **A repo file with `shared_pr_max` fails.** The key is now an unknown setting.
- **More PRs to review.** A run can open one PR for each file. The token ceiling and the steps of each attempt still limit the work.
- **A ticket that needs a change in `.github/` cannot be fixed.** The attempt fails, and the ticket gets the label `veil-failed-fix`. A person fixes it.
