# Grouping Fixes into PRs

The Engine puts Gozu Tickets into groups. Each group gets one draft Fix PR. A Shared PR carries Low and Medium Fixes. A High PR carries one High Fix, or the High Fixes that change the same file.

## What we decided

- **The group key.** A Shared PR is for one repository and one Source PR branch. Ticket GR-16 says "one for each repository". A PR has one base branch (ADR 0004), and tickets of different Source PRs have different bases. So the repository alone cannot be the key.
- **One checkout for each group.** The Fixes of a group build on each other. Each Fix has its own commit. A later ticket sees the earlier Fixes, so two Fixes cannot conflict.
- **A failed attempt discards its edits.** The strong attempt then starts from the last commit of the group. This is the same clean state as the fresh checkout of ticket GR-14, but it keeps the earlier Fixes. The repo provider gets one more operation, `discard_changes`.
- **Overlap means the same file.** High tickets that flag the same file in the same Source PR go into one PR. The body of the PR gives the reason.
- **High groups first.** The Engine fixes High groups before the shared groups. Then low-risk work does not delay high-risk work.
- **Failed Fixes stay out.** A PR holds only the Fixes that passed. A failed attempt leaves no edit in it.
- **The token ceiling.** If the ceiling stops a run in the middle of a group, the Engine still publishes the Fixes that passed. The current ticket and the later tickets wait for the next run.
- **The cap of the Shared PR.** A Shared PR holds at most 10 tickets (a setting). The other tickets wait for the next run.
- **Unknown severity is High.** A severity word that is not in the severity map gets its own PR, so a person looks at it. A severity map that a caller gives changes only its own words. The other words keep the default.
- **`finish` has a format.** The model gives a one-line commit message and an explanation of at most 3 sentences. The commit message becomes the commit. The explanation goes in the PR body and in the comment on the ticket.
- **Settings.** The severity map, the branch prefix, the cap of the Shared PR and the number of sentences are settings. The safety rules are not. The branch prefix feeds the no-loop rule, so it must have at least 3 characters and end with `/` or `-`.
- **The branch name.** A Shared PR branch names the first Fix that passed, not the first ticket. A ticket that failed gives no name.

## What we accept for now

- A later run makes a new Shared PR with a new branch for tickets that came later. The Engine does not add commits to an open Shared PR.
- If the repo provider fails while it commits or opens the PR, the run stops. The tickets of that group get no outcome and no tracker change. The next run tries them again.
- The explanation and the commit message are text from the model. The secret scan of ticket GR-17 must scan them.
