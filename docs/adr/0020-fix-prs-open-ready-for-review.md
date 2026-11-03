# Fix PRs open ready for review

Until now the Engine opened every Fix PR as a draft. "Drafts only" was a safety rule in the code.

## What we decided

- A Fix PR opens ready for review. It is not a draft.
- This replaces the rule "drafts only". The owner of the project decided it on 2026-10-31. A person marked the first PR ready by hand each time, so the draft gave no extra safety.
- The other safety rules stay. The Engine never merges. It never touches the default branch. It never edits `.github/workflows/`. A person reviews and merges every Fix PR.
- A PR of one ticket has no Summary section. Its ticket section says why, what changed and what it solves. A PR of several tickets starts with the reason for the group.

## What this costs

A ready PR can be merged at once. A branch rule that needs a review before merge is now the only guard on the Source PR branch. Turn that rule on in the repo.
