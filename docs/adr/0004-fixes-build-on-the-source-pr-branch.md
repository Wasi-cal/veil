# Fixes build on the Source PR branch

Gozu scans a repository when a developer raises a pull request (PR). Each Gozu Ticket belongs to an open PR, the Source PR. The finding is in the branch of that PR.

The Engine uses the branch of the Source PR, not the default branch:

- The checkout is the branch of the Source PR. The Fix commit starts from that branch.
- The draft Fix PR targets that branch.
- The Engine pushes only its own `gozu/fix-*` branch. It never pushes to the Source PR branch or to the default branch.
- The Engine skips a ticket when its Source PR is not open. The Source PR can be merged or closed, or the branch can have no PR. The reason in the run report is `source_pr_not_open`.

We chose this because a finding can be in code that does not exist on the default branch. The file can be missing, and the line numbers can differ.

This replaces the line in GR-8 and GR-10 that says the checkout is a shallow checkout of the default branch.

## Gaps that we accept for now

- The Engine checks the Source PR once, before the first attempt. If the developer closes or merges the PR while the model works, the Engine still opens the Fix PR.
- The ticket line can be out of date if the developer pushes new commits after the scan. The model sees the code around the line. If the code does not match, the attempt gives up.
- A PR from a fork does not count as a Source PR. The repo provider must match only PRs whose head branch is in the same repository.
- Two tickets on one Source PR give two Fix PRs. Both start from the same commit, so they can conflict. Ticket GR-16 groups Fixes and removes this problem.
- The Engine passes the branch name to the repo provider as it is. The provider must treat it as data and refuse a name that git can read as an option.
