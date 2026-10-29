# The GitHub adapter (the real repo provider)

An adapter is a part that talks to an outside service. This adapter is the real repo provider. It lets the Engine work on real GitHub repositories. Git makes the checkouts and the pushes. The GitHub REST API (the web service of GitHub) finds and opens pull requests. ADR 0007 gives the reasons for this design. The Engine calls this adapter through the `RepoProvider` and `Workspace` interfaces. Part 02 (the Engine) describes the caller. Part 04 (the RepoProvider and Workspace interfaces) describes the interfaces. Part 07 (the shared HTTP code) describes `call_json`, which sends every GitHub API request.

## The flow

1. The Shell builds a `GitHubRepoProvider` (in `provider.py`). It gives the provider a token, a `GitHubApi` object and a function that makes the remote URL of a repository. In production the API object is `HttpGitHubApi` (in `http_api.py`).
2. The Engine asks `has_open_pr` whether a Source PR is still open for a branch. The provider asks the API for the PRs with that head branch. The answer is yes only if one PR is open and its head repository is the same repository. A PR from a fork does not count.
3. The Engine asks `find_existing_fix` whether a Fix already exists for a ticket. The provider asks the API for the PRs that carry the issue label. It keeps the PRs whose head repository is this repository and whose base branch is the Source PR branch.
4. If one kept PR is open, `find_existing_fix` answers `OPEN_PR`. If none is open, it looks for a closed PR. The closed PR must have a head branch that starts with the branch prefix. The branch must still exist on the remote. `_branch_exists` checks this with `git ls-remote`. If so, the answer is `FIX_BRANCH`. A merged PR does not count. Otherwise the answer is no Fix (`None`).
5. The Engine asks `open_workspace` for a checkout of the Source PR branch. The provider refuses a branch name that starts with a dash. It makes a new private folder with `tempfile.mkdtemp`. It builds the git environment for this folder with `git_environment`.
6. The provider runs a shallow clone with `run_git`. The clone has depth 1, one branch and no tags. The token goes only in a per-command header that the environment sets for github.com. The remote URL has no token. The file `.git/config` never holds the token.
7. If the clone fails, the provider deletes the new folder at once and raises the error. If the clone works, the provider keeps the folder in its list and returns a `GitWorkspace` (in `workspace.py`) for the clone.
8. The Engine reads files, lists files and writes files through the `GitWorkspace`. Every file path goes through `_inside`. It refuses a path outside the checkout. This covers `..`, an absolute path and a symlink that points outside.
9. The Engine calls `commit` to make a Fix branch with the changes. It calls `discard_changes` to undo the work on a Fix that fails a check.
10. The Engine asks `open_draft_pr` to publish a Fix. The provider first refuses a head branch that starts with a dash. It refuses a head branch that does not start with the branch prefix. It refuses a head branch that equals the base branch. The Engine bases the Fix PR on the Source PR branch. So the Source PR branch never becomes a head.
11. The provider asks the API for PRs with that head branch. If one is open and comes from this repository, the provider returns its URL. It pushes nothing and opens no second PR.
12. Otherwise the provider searches its checkouts of this repository for the first one that holds the Fix branch. It calls `push` on that checkout. `push` sends only `refs/heads/<fix branch>` to the same name on the remote. It never uses force. It never pushes the Source PR branch or the default branch. If no checkout holds the branch, the provider raises an error.
13. The provider calls `create_draft_pr` on the API. The API adapter makes one draft PR. It adds the labels in a second call. The provider returns the PR URL. The provider never merges a PR.
14. The Shell calls `close` in a `finally` step. `close` deletes every checkout folder that the provider made and forgets the checkouts. The provider also works as a context manager, and leaving the `with` block calls `close`.
15. Every failure raises `RepoProviderError`. The adapter hides the token and its base64 form in the message first.

## Files

### constants/git.py

This file holds the fixed values that git commands use. It is a separate file so that the safety values have one place.

- `GITHUB_URL` — the text `https://github.com/`. The token header applies to this address only.
- `TOKEN_USER` — the user name `x-access-token`. GitHub accepts any user name when the password is a token. This is the name in the GitHub docs.
- `REF_PREFIX` — the text `refs/heads/`. It marks a branch name in a full git reference.
- `AUTHOR_NAME` — the text `Gozu Veil`. It is the name on every commit.
- `AUTHOR_EMAIL` — the text `veil@gozu.invalid`. It is the email on every commit. The `.invalid` end means that it cannot receive mail.
- `NETWORK_VARIABLES` — the list of 11 environment variable names that git may keep. These are the proxy variables (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` and the lowercase forms) and the certificate variables (`SSL_CERT_FILE`, `SSL_CERT_DIR`, `GIT_SSL_CAINFO`). Git needs them to reach GitHub through a proxy or with a company certificate.

### constants/http.py

This file holds the fixed values for the GitHub API.

- `API_URL` — the address `https://api.github.com`. It is the default base address of `HttpGitHubApi`.
- `API_VERSION` — the text `2022-11-28`. The adapter sends it in the `X-GitHub-Api-Version` header.
- `PAGE_SIZE` — the number 100. It is the most PRs that one API call reads.

### constants/modes.py

This file holds a folder permission value.

- `DIR_MODE` — the octal value `0o700`. Only the owner can read, write or enter a folder with this mode. The provider uses it for the temporary root folder when the caller gives one.

### constants/pr_states.py

This file holds the three states of a PR.

- `PrState` — a type that allows only the words `open`, `closed` and `merged`.
- `OPEN` — the word `open`.
- `CLOSED` — the word `closed`.
- `MERGED` — the word `merged`. GitHub reports a merged PR as closed. The adapter changes the state to `merged` when the PR has a merge time.

### constants/repo_name.py

This file holds the pattern for a repository name.

- `REPO_NAME` — a pattern for the form `owner/name`. Each part may hold only letters, digits, underscore, dot and hyphen. No other character can change a URL.

### models/pull_request.py

This file holds the record of one PR. It is separate so that the API and the provider share one shape.

- `PullRequest` — a pydantic model (a checked record) for a PR as the GitHub API shows it. It is frozen, so no code can change a field after the record exists. Its fields follow.
- `url` — the web address of the PR.
- `base_repo` — the full name of the repository that receives the PR.
- `head_repo` — the full name of the repository that holds the head branch. It is an empty text when someone deleted the fork. This field tells a fork PR from a same-repository PR.
- `head_branch` — the name of the branch that holds the changes.
- `base_branch` — the name of the branch that the PR targets.
- `state` — one of `open`, `closed` or `merged`.
- `labels` — the names of the labels on the PR, as a tuple.
- `title` — the title of the PR.
- `body` — the description text of the PR.
- `draft` — true if the PR is a draft.

### api.py

This file defines the list of API operations that the provider needs. A Protocol is a list of methods that a part must have. It is its own file so that tests can use a stub in place of the real HTTP code. This is the seam that ADR 0007 names.

- `GitHubApi` — a Protocol for the part of the GitHub API that the provider needs. A PR has one of three states. `HttpGitHubApi` is the real one.
- `GitHubApi.find_pull_requests(repo, head, label)` — returns the PRs of a repository in every state. It filters by head branch and by label when given. The head is a branch name without an owner. A fork PR can have the same branch name. The provider calls it.
- `GitHubApi.create_draft_pr(repo, head, base, title, body, labels)` — opens a draft PR from a branch of the repository and puts the labels on it. It returns the new `PullRequest`. The provider calls it.

### http_api.py

This file is the real GitHub API client. It builds each request and turns each reply into a `PullRequest`. The shared HTTP code of part 07 sends the request.

- `HttpGitHubApi` — the GitHub REST API over HTTP. The token goes in the Authorization header and nowhere else. One call reads one page of at most 100 PRs.
- `HttpGitHubApi.__init__(token, base_url)` — stores the token and the base address. It first calls `require_https`. It raises `RepoProviderError` for an address that is not https. Only a local host may use http, so tests can use a local server. It strips a trailing slash from the address.
- `HttpGitHubApi.find_pull_requests(repo, head, label)` — returns PRs as `PullRequest` records. It first checks the repository name. With a label, it searches issues for `repo:<repo> is:pr label:"<label>"`. It then reads each found PR on its own, because the search reply does not hold the head and base details. Without a label, it lists PRs of every state. If the caller gives a head, it asks for `<owner>:<head>`. In both cases, when the caller gives a head, it keeps only PRs whose head branch equals it.
- `HttpGitHubApi.create_draft_pr(repo, head, base, title, body, labels)` — checks the repository name. It sends a POST that creates a PR with the draft flag on. If the caller gives labels, it sends a second POST to add them. It then puts the labels on the record by hand. It returns the `PullRequest`.
- `HttpGitHubApi._check_repo(repo)` — a static method. It raises `RepoProviderError` with the message "Refused the repository name." if the name does not match `REPO_NAME` or holds `..`. Both public methods call it first.
- `HttpGitHubApi._pull_request(item)` — a static method. It turns one GitHub reply item into a `PullRequest`. The head repository name is empty if the fork is gone. The state is `merged` if the item has a merge time. Otherwise it is the state that GitHub gives. A missing title or body becomes an empty text.
- `HttpGitHubApi._call(method, path, params, body)` — sends one request through `call_json`. It sets the headers `Authorization` (a bearer token), `Accept` and `X-GitHub-Api-Version`. It gives the token to `call_json` so that errors hide it. An empty reply raises `RepoProviderError`. It returns the decoded JSON.

### git_command.py

This file runs git and builds the safe environment for it. It is separate so that the workspace and the provider share the same safety code.

- `refuse_option_like(name)` — raises `RepoProviderError` if a branch name is empty or starts with a dash. Git can read such a name as an option. It returns nothing otherwise. The provider and the workspace call it.
- `_basic_credential(token)` — joins `TOKEN_USER` and the token with a colon and encodes the text in base64. It returns the encoded text. `secret_values` and `git_environment` call it.
- `secret_values(token)` — returns a tuple of two values: the token and its base64 form. Every git error hides both. The provider calls it.
- `git_environment(token, home)` — builds the only environment variables that a git child process gets. It keeps the network variables that exist in the current environment. It adds `PATH`, a private `HOME`, `LANG` set to `C` and the author and committer names and emails. It turns off terminal prompts. It ignores the system and global git config. It adds one config entry through `GIT_CONFIG_*` variables. That entry is an Authorization header for `https://github.com/` only. Git does not write this header to `.git/config`. It returns the dictionary.
- `run_git(cwd, env, secrets, *args)` — runs git with the given arguments, folder and environment. It returns the standard output as text. If git fails, it raises `RepoProviderError` with the text `git <command> failed.` and the git error output. It hides the secret values first. It does not keep the original error as a cause, so no secret leaks through a traceback.

### workspace.py

This file is one git checkout that the Engine edits. It satisfies the `Workspace` interface of part 04. It is separate from the provider because one provider makes many checkouts.

- `GitWorkspace` — one private git checkout. It has the public attribute `path`, which is the checkout folder.
- `GitWorkspace.__init__(path, env, secrets)` — stores the checkout path, the git environment and the secret values. The provider calls it.
- `GitWorkspace._git(*args)` — runs git in the checkout through `run_git`. It returns the output text.
- `GitWorkspace._inside(path)` — turns a relative file name into a full path. It follows symlinks first. It raises `RepoProviderError` with the message "Refused a path outside the checkout." if the name is absolute or the result leaves the checkout. This covers `..` and a symlink that points outside. Every read and write calls it.
- `GitWorkspace.read_file(path)` — reads a file in the checkout and returns the text. The path goes through `_inside`.
- `GitWorkspace.list_files()` — returns the list of files that git tracks, from `git ls-files`. It splits the output at a zero character, so names with odd characters work.
- `GitWorkspace.write_file(path, content)` — writes the text to a file in the checkout. The path goes through `_inside`. It returns nothing.
- `GitWorkspace.commit(branch, message)` — refuses an option-like branch name. It then runs `git checkout -B <branch>` to make or reset the branch. It stages all changes with `git add -A`. It makes one commit with the message.
- `GitWorkspace.has_branch(branch)` — returns true if a local branch with this name exists. It uses `git branch --list` with `--` before the name. The provider calls it.
- `GitWorkspace.push(branch)` — refuses an option-like name. It pushes the local branch to the branch of the same name on `origin`, with the full reference on both sides. It never uses force. It never pushes another reference. The provider calls it.
- `GitWorkspace.discard_changes()` — restores all tracked files to the last commit in the index and the working folder. It then deletes untracked files and folders. The Engine calls it to drop the work of a Fix that failed.

### provider.py

This file is the real repo provider. It joins git and the API and owns the temporary folders. It is its own file because it holds the state of a run: the token, the checkouts and the folder list.

- `_same_repo(head_repo, repo)` — returns true if the head repository name is not empty and equals the repository name without regard to letter case. GitHub names repositories without case. A deleted fork has an empty name, so it never matches.
- `GitHubRepoProvider` — the real repo provider. Each checkout is a private temporary folder. The caller must call `close` in a `finally` step.
- `GitHubRepoProvider.__init__(token, api, remote_url, branch_prefix, temp_root)` — stores five values. They are the token, the API object, the function that makes a remote URL, the branch prefix and the temporary root. The token is a `SecretStr`, a value that hides itself when printed. The prefix defaults to `FIX_BRANCH_PREFIX`, which is `gozu/fix-`. If the caller gives a temporary root, it makes that folder with mode `DIR_MODE`. It starts with an empty folder list and an empty checkout map.
- `GitHubRepoProvider.__enter__()` — returns the provider, so a `with` block can use it.
- `GitHubRepoProvider.__exit__(*_exc)` — calls `close` when the `with` block ends, even after an error.
- `GitHubRepoProvider.close()` — deletes every checkout folder that the provider made. It ignores errors on delete. It then clears the folder list and the checkout map. The Shell calls it.
- `GitHubRepoProvider.has_open_pr(repo, branch)` — returns true if an open PR with this head branch comes from the same repository. The Engine calls it.
- `GitHubRepoProvider.find_existing_fix(query)` — answers `OPEN_PR`, `FIX_BRANCH` or `None` for a `FixQuery`. It uses the rules in steps 3 and 4 of the flow. The Engine calls it.
- `GitHubRepoProvider._branch_exists(repo, branch)` — makes a short-lived temporary folder and runs `git ls-remote --heads` for the branch. It returns true if the answer has text. The call deletes the folder when it ends. `find_existing_fix` calls it.
- `GitHubRepoProvider.open_workspace(repo, branch)` — makes a shallow checkout, as steps 5 to 7 describe. It returns a `GitWorkspace`. It records the folder for `close` and records the workspace for `open_draft_pr`. The Engine calls it.
- `GitHubRepoProvider.open_draft_pr(draft)` — checks the head branch, reuses an open PR, pushes the Fix branch and opens one draft PR, as steps 10 to 13 describe. It returns the PR URL. The Engine calls it with a `DraftPr`.

## Things to know

- The provider refuses to push a branch that does not start with the branch prefix `gozu/fix-` (when the caller keeps the default). It also refuses a head that equals the base. The push sends one explicit reference and never uses force. So the Source PR branch and the default branch cannot be pushed.
- `refuse_option_like` runs on every branch name before git sees it. A name that starts with a dash raises an error. Git commands also put `--` before the name when git supports it.
- The token reaches git only through a per-command header for `https://github.com/`. The remote URL and `.git/config` never hold it. A git child process gets a small environment and a private `HOME`, not the full environment of the Engine.
- `HttpGitHubApi` never follows a redirect, because the shared HTTP code treats a redirect as a failure. So the token cannot reach another host. It also refuses a base address that is not https, except for a local host.
- One API call reads at most 100 PRs, so a repository with more matching PRs can hide an older one. A label search also costs one extra call for each PR found. The label search of GitHub can lag, so a PR that is only seconds old can be missing.
- A PR for a branch can exist without labels if the second call that adds them fails. The next run then does not find it as an existing Fix. Two runs at the same time can both pass the open PR check. The second PR call then fails with a GitHub error, and the provider does not look up the first PR again. A Shell that skips `close` leaves checkouts in the temporary folder.
