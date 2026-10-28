# The real repo provider

The real repo provider is `GitHubRepoProvider` in `veil/adapters/github/`. Git does the checkouts and the pushes. The GitHub REST API does the PR work (ticket GR-18).

## What we decided

- **Two parts.** Git runs as a child process. The GitHub API sits behind a small interface, `GitHubApi`. The interface has a real HTTP adapter and a test stub, so the seam is real. Git has no seam. Tests run real git against a local bare remote.
- **The checkout.** It is a shallow clone (depth 1) of the Source PR branch, as ADR 0004 says. It goes in a private directory (mode 0700). A failed clone deletes the directory at once. `close()` deletes all the others. The Shell calls `close()` in a `finally` step.
- **The token.** It goes to git in a per-command header (`GIT_CONFIG_*` variables) for github.com only. The remote URL is plain, and `.git/config` never holds the token. A git child process gets only `PATH`, a private `HOME`, the identity of the author and these config variables. The API adapter sends the token in the Authorization header only.
- **Errors.** The adapter raises `RepoProviderError` (in `engine/errors`). It hides credential values first, with `redact`. `run()` still stops on this error, as ADR 0005 accepts. The Shell decides on a retry.
- **Source PR.** `has_open_pr` is true for an open PR whose head repository is this repository. A fork PR does not count.
- **Existing Fix.** An open PR that carries the issue label, comes from this repository and has the Source PR branch as base is `open_pr`. A closed PR that is not merged counts as `fix_branch`. It must carry the label, start with the branch prefix and have a branch that still exists. A merged PR does not count. A GitHub branch cannot carry a label, so the label of the closed PR stands for the branch.
- **Paths and redirects.** A workspace refuses a path that leaves the checkout. This covers `..`, an absolute path and a symlink that points outside. The API adapter never follows a redirect, so the token cannot reach another host. Git gets the proxy and certificate variables that it needs.
- **Draft PR.** The provider pushes one ref, `refs/heads/<fix branch>`, never with force. It refuses a head that does not start with the branch prefix and a head that equals the base. It returns the URL of an open PR for the head and makes no second PR. It never merges.

## What we accept for now

- One API call reads at most 100 PRs. A repository with more matching PRs can hide an older one.
- A Fix PR that someone closed and deleted the branch of looks like no Fix. The next run makes a new one.
- The tests do not prove that git sends the token header to github.com. They prove that the token is not on disk and not in errors.
- A Shell that does not call `close()` leaves checkouts in the temporary directory.
- A PR for a branch can exist without labels. The labels come in a second call. If that call fails, the next run does not find the PR as an existing Fix.
- Two runs at the same time can both pass the check for an open PR. The second PR call then fails with an error from GitHub. The provider does not look up the first PR again.
- A closed PR for a Fix branch does not stop a new PR for the same branch.
- The label search of GitHub can lag. A PR that is only seconds old can be missing.
- The provider does not list repos in scope. The interface has no such operation. Each Shell does this, and tickets GR-24 and GR-25 wire the provider in.
- No shared tests run on both the fake provider and the real one. The real provider has its own tests with the same rules.
