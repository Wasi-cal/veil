# Refuse symlinks in the workspace

The owner of the project decided this on 2026-11-03, after the security review of the release.

## The problem

The Engine checks the text of a path. It refuses `.github/` and secret files such as `.env`. A tracked symlink can hide the real path. The link `docs/ci.yml` can point at `.github/workflows/ci.yml`. The text `docs/ci.yml` passes the check. The workspace then reads and writes the real file. `git add -A` commits the change.

The reviewers rated this LOW. The attacker needs write access to the repo already, and a person reviews the Fix PR. It still broke a rule that the project states, so we closed it.

## What we decided

- **The workspace refuses a path that holds a symlink.** It checks the file and every folder in the path. This holds for a link that points inside the checkout and for a link that points outside.
- **The refusal is a `FileNotFoundError`.** The Engine already treats it as "not a file of the repo". A read returns an error text to the model. An edit is refused. A ticket on a symlink becomes a Failed Fix. A planted symlink cannot stop the run.
- **A path with `..` or an absolute path is still a `RepoProviderError`.** The Engine rules refuse these before they reach the workspace.
- **The listing hides symlinks.** `list_files` reads the mode of each entry (`git ls-files -s`) and skips mode `120000`. So `search` and `list_dir` never show a link.

## What we accept

- **A repo that uses symlinks on purpose.** A ticket on such a link is a Failed Fix. A ticket on the real file works.
- **No check of the final list of changed paths.** The checks above make it unneeded today. A check before each commit would add a new method to the `Workspace` interface.
