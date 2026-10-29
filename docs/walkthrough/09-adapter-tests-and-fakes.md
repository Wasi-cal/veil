# The adapter tests and the fakes

This part covers the tests of the three adapters (GitHub, Jira and OpenAI) and the stand-in parts that the tests use. An adapter is a part that talks to an outside service. The tests prove that each adapter sends the right requests, reads the answers, and never leaks a Credential. The fakes let the tests run with no network and no real account.

## The flow

There are two kinds of stand-in. Each kind serves a different test.

1. A fake part behaves like the real part, but it keeps everything in memory or in local folders. `FakeTracker`, `FakeRepoProvider` and `FakeModelClient` are of this kind. The Engine tests use them. Part 08 (the Engine tests) covers those tests.
2. A stub server replays recorded JSON answers over real HTTP. `StubHttpServer` is of this kind. The adapter tests use it, so the real adapter code runs, including its HTTP client. Parts 05 to 07 (the adapters) cover the code under test.
3. Two smaller stubs sit between these kinds. `StubGitHubApi` and `StubOpenAIApi` replace only the API layer of an adapter. They let the tests check the adapter logic above that layer with no HTTP.
4. The answers that the stub server replays come from the fixture files. `github_fixtures.py` builds GitHub pull request answers. `jira_fixtures.py` and `openai_fixtures.py` build Jira and OpenAI answers.
5. A person wrote the Jira and OpenAI answers by hand from the public documents of those services. Nobody recorded them from a live call. The test data can differ from a real answer if the documents are wrong or old.
6. A typical adapter test starts with a `with StubHttpServer() as server:` block. This starts a small web server on `127.0.0.1` and a free port. The block stops the server when it ends.
7. The test fills `server.routes`. A route maps a method and a path to a status, a JSON body and optional headers. A list of answers plays in order, and the last answer repeats.
8. The test builds the real adapter and points it at `server.url`. For Jira, `make_tracker` does this. For GitHub and OpenAI, the test builds `HttpGitHubApi` or `HttpOpenAIApi` with `base_url=server.url`.
9. The test calls one method of the adapter, for example `open_tickets` or `create_response`.
10. The `Handler` inside `StubHttpServer` receives the request. It saves a `SeenRequest` in `server.seen`, waits for `delay_seconds`, and sends the answer for the route. A route that does not exist gets a 404 answer.
11. The test checks the result. It also reads `server.seen` to check what the adapter sent, for example the method, the query, the `Authorization` header and the body.
12. Many tests check a rule of safety. The adapter must raise its own error type. The error text must not hold the Credential. A redirect must not carry the Credential to another host. A test shows this when `server.seen` of the second server stays empty.
13. The GitHub tests that need git use real git on local folders. `make_remote` builds a bare repository that acts as the remote. `make_provider` points the provider at it with a `file://` address.

## Files

### tests/fakes/http_server.py

This file holds the stub server for the adapter tests. It is its own file because all three adapters share it.

- `SeenRequest` — a pydantic model (a checked record) of one request that the server received. Its fields follow.
- `SeenRequest.method` — the HTTP method, for example `GET` or `POST`.
- `SeenRequest.path` — the path of the request, without the query text.
- `SeenRequest.query` — the query parameters. Each name maps to a list of values.
- `SeenRequest.authorization` — the value of the `Authorization` header, or nothing if the request had none.
- `SeenRequest.body` — the JSON body that the request carried, or nothing if the body was empty.
- `StubHttpServer` — a local HTTP server that replays recorded answers. A test uses it as a context manager. It has the public parts `routes`, `seen`, `delay_seconds` and `url`.
- `StubHttpServer.__init__(self)` — builds the server on `127.0.0.1` with a free port. It sets empty `routes` and `seen` lists and a delay of 0 seconds. It builds the thread but does not start it. Called by each test.
- `Handler` — the request handler class that `__init__` defines inside itself. It maps `GET`, `POST` and `PUT` to `_answer`.
- `Handler._answer(self)` — reads the request, saves a `SeenRequest`, waits for the delay, and sends the answer. It takes the answer from `routes` by method and path. It sends 404 with `Not Found` when no route exists. It takes the first answer from a list and keeps the last answer. It adds the extra headers of the answer, for example `Location`. It always sends JSON.
- `Handler.log_message(self, *_args)` — does nothing, so the server writes no log lines during tests.
- `StubHttpServer.__enter__(self)` — starts the server thread and returns the server.
- `StubHttpServer.__exit__(self, *_exc)` — stops the server and closes its port. A call to the server after this fails with a refused connection. Tests use this to simulate a server that is down.

### tests/fakes/github_fixtures.py

This file builds the GitHub pull request answers that the stub server replays. It keeps only the fields that the GitHub adapter reads.

- `pull_json(number, head, base, state, merged, head_repo, labels, draft)` — builds the JSON of one pull request. The defaults are number 1, head `feature-x`, base `main`, state `open` and repository `acme/app`. A merged pull request gets a `merged_at` date. The labels become a list of name records. It returns a dictionary. The GitHub HTTP tests call it.

### tests/fakes/jira_fixtures.py

This file builds Jira Cloud REST v3 answers. The ticket text follows what Gozurion writes. A person wrote the answers by hand from the Jira documents. Nobody recorded them from a live site.

- `_paragraph(text)` — builds one paragraph in the Atlassian document format (ADF). It returns a dictionary. The other builders in this file call it.
- `adf_description(summary, details, full)` — builds the ticket description that Gozurion writes. It holds a short paragraph, an optional expandable full text, a heading `Details`, and a bullet list of the detail lines. It returns a document dictionary. `issue_json` calls it.
- `gozurion_details(repo, component, line, severity, branch)` — builds the list of detail lines of a Gozu Ticket. The defaults are repository `acme/app`, component `acme_app:src/app.py`, line 3, severity `HIGH` and branch `feature/login`. It leaves out the line when `line` is nothing. It adds fixed lines for the type, the rule, the source and the commit. It returns a list of text lines.
- `issue_json(key, labels, details, summary, full, extra_fields)` — builds the JSON of one Jira issue. The default key is `SEC-7`. The default labels are an issue label, a branch label and the eligible label `veil-eligible`. It builds the description with `adf_description`. It adds the extra fields, for example custom fields. It returns a dictionary.
- `search_page(issues, next_page_token)` — builds one page of search results. It adds `nextPageToken` only when the caller gives a token. It returns a dictionary.

### tests/fakes/openai_fixtures.py

This file builds OpenAI Responses API answers. The fields follow the public API reference. A person wrote them by hand. Nobody recorded them from a live call.

- `function_call_item(call_id, name, arguments)` — builds one output item of type `function_call`. The `arguments` value is the JSON text that the model wrote. It returns a dictionary.
- `message_item(text)` — builds one output item of type `message` with a text part. It returns a dictionary. The adapter must ignore it.
- `reasoning_item()` — builds one output item of type `reasoning` with an empty summary. It returns a dictionary. The adapter must ignore it.
- `response_json(output, usage, status, error, incomplete_details)` — builds a whole reply. The default status is `completed`. The default usage is 100 input tokens, 20 output tokens and 120 total tokens. It returns a dictionary.

### tests/fakes/github_api.py

This file holds a stub of the GitHub API layer that keeps its pull requests in a list. The provider tests use it so they need no HTTP.

- `StubGitHubApi` — a GitHub API that keeps pull requests in a list. It filters as the real API does. It has the lists `pull_requests` and `created`.
- `StubGitHubApi.__init__(self, pull_requests)` — copies the given pull requests into `pull_requests`. It starts `created` as an empty list.
- `StubGitHubApi.find_pull_requests(self, repo, head, label)` — returns the pull requests whose base repository equals `repo`. It also filters by head branch and by label when the caller gives them. It returns a list of `PullRequest` records.
- `StubGitHubApi.create_draft_pr(self, repo, head, base, title, body, labels)` — makes an open draft `PullRequest` with a fake address. The number in the address is the count of known pull requests plus one. It saves the record in both lists. It returns the record.

### tests/fakes/openai_api.py

This file holds a stub of the OpenAI API layer that plays a list of replies. The client tests use it so they need no HTTP.

- `api_reply(*calls, tokens)` — builds an `ApiResponse`. Each call is a tuple of a call id, a tool name and the JSON text of the arguments. The default token count is 10. It returns the `ApiResponse`.
- `StubOpenAIApi` — an OpenAI API that plays a list of replies. It raises a reply that is an exception. It keeps the list `requests`.
- `StubOpenAIApi.__init__(self, replies)` — copies the replies and starts an empty `requests` list.
- `StubOpenAIApi.create_response(self, model, input_items, tools)` — saves the model, the input and the tools in `requests`. It takes the next reply. It raises the reply if the reply is an exception. Otherwise it returns the reply.

### tests/fakes/tracker.py

This file holds the fake tracker for the Engine tests. A tracker is the part that holds the tickets. The fake keeps everything in memory.

- `make_ticket(key, repo, file, line, severity, finding, branch, labels)` — builds a Gozu Ticket as an Engine `Ticket`. The defaults are key `GR-100`, repository `acme/app`, file `app.py`, line 1, severity `Medium`, branch `feature`. By default each key gets its own label `issue-` plus the lower case key. It returns a `Ticket`.
- `FakeTracker` — a fake of the tracker. It keeps tickets, statuses, comments and labels in memory.
- `FakeTracker.__init__(self, tickets)` — saves the tickets. It sets each status to `To Do` and starts empty comment and label lists for each key.
- `FakeTracker.explode_on_next_comment(self)` — makes the next `add_comment` raise one error. It simulates a tracker that is down.
- `FakeTracker.open_tickets(self)` — returns copies of the tickets. Each copy carries the labels that the Engine added, as a real tracker does.
- `FakeTracker.add_comment(self, key, text)` — saves the comment for the key. It raises `RuntimeError` once if a test called `explode_on_next_comment` before.
- `FakeTracker.set_status(self, key, status)` — saves the new status of the ticket.
- `FakeTracker.add_label(self, key, label)` — adds a label to the ticket.
- `FakeTracker.remove_label(self, key, label)` — removes a label. It simulates a person who removes a label in the tracker.
- `FakeTracker.labels_on(self, key)` — returns a copy of the labels that the Engine added to the ticket. A test calls it.
- `FakeTracker.status_of(self, key)` — returns the status of the ticket. A test calls it.
- `FakeTracker.comments_on(self, key)` — returns a copy of the comments on the ticket. A test calls it.

### tests/fakes/model.py

This file holds the fake model client for the Engine tests. It plays a script of tool calls, so no real model runs. It also holds helpers that build the tool calls of the script.

- `edit_file(path, old, new)` — builds a `ToolCall` for the tool `edit_file`. It replaces the text `old` with `new` in `path`.
- `read_file(path, **arguments)` — builds a `ToolCall` for the tool `read_file`. Extra arguments go into the call.
- `search(pattern, **arguments)` — builds a `ToolCall` for the tool `search`. Extra arguments go into the call.
- `list_dir(path)` — builds a `ToolCall` for the tool `list_dir`. The default path is `.`.
- `finish(explanation, commit_message)` — builds a `ToolCall` for the tool `finish`. The defaults are `Fixed.` and `Fix the finding.`.
- `FakeModelClient` — a model client that plays a script. Each model call returns one list of tool calls. A list gives one script for every model. A dictionary gives one script for each model name.
- `FakeModelClient.__init__(self, script, tokens_per_call)` — saves the script. It starts the records `received`, `tools_received` and `models_used`, and a call counter. The default token count of each call is 0.
- `FakeModelClient.everything_received(self)` — joins every message that the model received into one text. It uses the tool calls as JSON text when a message has no content. A test calls it.
- `FakeModelClient.sent_by_the_engine(self)` — joins every message that the Engine wrote for the model. It leaves out the assistant messages, which are the tool calls of the model. A test calls it.
- `FakeModelClient.first_prompt(self)` — returns the text of the first user message of the first model call. A test calls it.
- `FakeModelClient.next(self, messages, model, tools)` — checks the conversation, saves what it received, and returns the next scripted reply. Each tool call gets an id of the form `call_` plus a running number. It returns a `ModelReply` with the call list and the token count. The Engine calls it.
- `_check_conversation(messages)` — refuses a conversation that a real API also refuses. A tool message that answers no earlier call of the model raises `ValueError`. `FakeModelClient.next` calls it.

### tests/fakes/repo.py

This file holds the fake repository provider for the Engine tests. It uses real local git repositories and has no network. Many tests need real git to check commits and branches, so the file exists on its own.

- `_git(cwd, *args)` — runs a git command in a folder with a fixed test name and email. It raises if git fails. It returns the output text. Other code in this file calls it.
- `FakePullRequest` — a pydantic model of a draft pull request that the fake opened. Its fields follow.
- `FakePullRequest.repo` — the repository name.
- `FakePullRequest.head` — the head branch of the pull request.
- `FakePullRequest.base` — the base branch of the pull request.
- `FakePullRequest.title` — the title.
- `FakePullRequest.body` — the body text.
- `FakePullRequest.draft` — true when the pull request is a draft.
- `FakePullRequest.url` — the fake address of the pull request.
- `FakeClone` — a pydantic model of one checkout that the Engine opened. The Fix commits come after its start branch.
- `FakeClone.repo` — the repository name.
- `FakeClone.path` — the folder of the checkout.
- `FakeClone.start_branch` — the branch that the checkout started from.
- `FakeRemoteFix` — a pydantic model of a Fix that the fake remote knows. It is an open pull request or a Fix branch.
- `FakeRemoteFix.repo` — the repository name.
- `FakeRemoteFix.kind` — the kind of Fix, `open_pr` or `fix_branch`.
- `FakeRemoteFix.branch` — the branch name.
- `FakeRemoteFix.base` — the base branch of an open pull request, or nothing if any base counts.
- `FakeRemoteFix.labels` — the labels that the pull request or branch carries.
- `FakeWorkspace` — a fake workspace that wraps one real checkout folder. The Engine uses it to read and change files.
- `FakeWorkspace.__init__(self, path)` — saves the folder.
- `FakeWorkspace.read_file(self, path)` — reads a file of the checkout as text. It returns the text.
- `FakeWorkspace.list_files(self)` — lists the files that git tracks. It returns a list of paths.
- `FakeWorkspace.write_file(self, path, content)` — writes the text to a file of the checkout.
- `FakeWorkspace.commit(self, branch, message)` — switches to the branch, creating it if needed, adds all files, and makes one commit.
- `FakeWorkspace.discard_changes(self)` — resets tracked files to the last commit and removes untracked files.
- `FakeRepoProvider` — a fake repository provider that uses real local git repositories. It has the list `pull_requests`.
- `FakeRepoProvider.__init__(self, root, repos, branch_prefix)` — saves the root folder and the prefix of Fix branches. The default prefix is `gozu/fix-`. For each repository it makes an origin repository on the branch `main`. It writes the given files and makes the first commit. The files may be text or bytes.
- `FakeRepoProvider.seed_source_pr(self, repo, branch, files, is_open)` — makes a branch from `main` with the given file changes and one commit, as a developer does for a Source PR. With `is_open` false the pull request has the state merged or closed, or it does not exist.
- `FakeRepoProvider.seed_pull_request(self, repo, branch, labels, base)` — puts an open pull request in the fake remote. An earlier run or a person made it. No base means any base.
- `FakeRepoProvider.seed_branch(self, repo, branch, labels)` — puts a Fix branch with these labels in the fake remote. No pull request is open.
- `FakeRepoProvider.open_workspace(self, repo, branch)` — refuses a branch name that starts with `-` and raises `ValueError`. Otherwise it clones the branch from the origin into a new numbered folder. It returns a `FakeWorkspace`. The Engine calls it.
- `FakeRepoProvider.has_open_pr(self, repo, branch)` — returns true when a test seeded the branch as an open Source PR. The Engine calls it.
- `FakeRepoProvider.find_existing_fix(self, query)` — looks in the fake remote for a Fix for the same repository and issue label. It returns `open_pr` if any match is an open pull request. Otherwise it returns the kind of the first match, or nothing. The Engine calls it.
- `FakeRepoProvider._matches(remote, query)` — a static method. An open pull request matches when its base is empty or equals the source branch of the query. A Fix branch matches when its name starts with the branch prefix of the query.
- `FakeRepoProvider.open_draft_pr(self, draft)` — refuses a head that lacks the Fix branch prefix or equals the base, and raises `ValueError`. It returns the old address when a pull request for the same head exists. Otherwise it pushes the head branch to the fake origin, records the pull request, and returns its fake address. The Engine calls it.
- `FakeRepoProvider.workspaces_opened(self)` — a property. It returns how many checkouts the Engine opened.
- `FakeRepoProvider.head_of(self, repo, branch)` — returns the commit that a branch points to in the fake origin.
- `FakeRepoProvider.commit_count_on(self, pr)` — returns how many Fix commits the pull request branch holds after its start branch.
- `FakeRepoProvider.commit_subjects_on(self, pr)` — returns the subject line of each Fix commit, oldest first.
- `FakeRepoProvider.commit_messages_on(self, pr)` — returns the whole message of each Fix commit, subject and body, oldest first.
- `FakeRepoProvider.file_on(self, pr, path)` — returns the text of a file as it is on the pull request branch.
- `FakeRepoProvider.changed_paths_on(self, pr)` — returns the set of paths that the Fix commits changed.
- `FakeRepoProvider._clone_with_branch(self, repo, branch)` — finds the checkout that holds the branch. It raises `LookupError` if none holds it. Other methods call it.

### tests/fakes/\_\_init\_\_.py

This file gathers the fakes for the Engine tests in one place. It imports `FakeModelClient`, the five tool call builders (`edit_file`, `finish`, `list_dir`, `read_file`, `search`), `FakeRepoProvider`, `FakeTracker` and `make_ticket`. It lists them in `__all__`. It has no functions of its own. It does not export the stub server or the fixtures.

### tests/adapters/github/support.py

This file holds the helpers that the GitHub adapter tests share. Several test files need a real bare git remote, so the helpers live in one file.

- `TOKEN` — a fake GitHub token that the file builds from pieces. Tests check that it never shows in errors, files or configuration.
- `git(cwd, *args)` — runs a git command in a folder with a fixed test name and email. It raises if git fails. It returns the output text.
- `make_remote(root, repo, branches)` — builds a bare git remote under `root`. It holds `main` with two commits and one extra commit on each branch of `branches`. It pushes everything. It returns the path of the bare repository.
- `make_provider(root, api, branch_prefix)` — builds a real `GitHubRepoProvider` with the fake token. The remote address points to the local bare repository. The temporary folder is `tmp` under `root`. The default prefix is `gozu/fix-`.

### tests/adapters/github/test_git_environment.py

This file proves that the git command gets the environment variables it needs and no others. It is separate because it tests one function and needs no remote.

- `test_git_gets_the_proxy_and_the_certificate_variables_that_it_needs` — the test sets proxy, certificate and cloud key variables. The environment for git keeps the proxy and the certificate variables and drops the cloud key.

### tests/adapters/github/test_http_api.py

This file proves that `HttpGitHubApi` sends the right requests to a stub server, reads the answers, and keeps the token safe.

- `api_for(server)` — builds an `HttpGitHubApi` with the fake token and the stub server address.
- `test_it_finds_the_pull_requests_of_a_head_branch_in_every_state` — the server returns open, merged, closed and fork pull requests. The adapter returns all four with the right states and repositories. It asks for all states, the head `acme:feature-x` and a bearer token.
- `test_it_finds_the_pull_requests_that_carry_a_label` — the server answers a search and a pull request read. The adapter returns the pull request with its branches and labels. The search text names the repository and the label.
- `test_it_opens_a_draft_pr_and_puts_the_labels_on_it` — the adapter creates a pull request and then sends the labels in a second request. The first body has the title, head, base, body and the draft flag. The second body has the labels.
- `test_an_api_error_raises_without_the_token` — the server answers 401 with a message that holds the token. The adapter raises `RepoProviderError` with the status and without the token.
- `test_it_refuses_a_repository_name_that_could_change_the_url` — the test gives four bad names. The adapter raises `RepoProviderError` and sends no request.
- `test_a_redirect_never_carries_the_token_to_another_host` — the server answers 302 to a second server. The adapter raises `RepoProviderError` and the second server sees no request.
- `test_the_adapter_refuses_a_url_that_is_not_https` — the test builds the adapter with an `http`, `file` or bare address. The adapter raises `RepoProviderError`.

### tests/adapters/github/test_checkout.py

This file proves that the provider opens checkouts safely with real git. It checks the content, the privacy, the cleanup and the refusal of bad paths and names.

- `FEATURE` — the files of the `feature-x` branch. `app.py` holds `value = 'feature'`.
- `provider_with_feature(tmp_path)` — makes a remote with a branch `feature-x` and a `tmp` folder. It returns a provider.
- `test_the_checkout_is_the_branch_of_the_source_pr` — the test opens `feature-x`. The workspace holds the file of that branch and lists only that file.
- `test_the_checkout_is_shallow_and_private` — the test opens a checkout. It holds one commit, and its parent folder has the mode `0o700`.
- `test_the_token_is_never_on_disk` — the test opens a checkout. The git configuration holds no token and no `extraheader`. The remote address is the plain address.
- `test_close_deletes_every_checkout` — the test opens two checkouts and calls `close`. The temporary folder is empty.
- `test_a_failed_checkout_leaves_no_directory_and_no_token` — the test opens a branch that does not exist. The provider raises `RepoProviderError` without the token and leaves no folder.
- `test_a_branch_name_that_git_reads_as_an_option_is_refused` — the test gives `-x`, `--upload-pack=evil` and an empty name. The provider raises `RepoProviderError` and leaves no folder.
- `test_each_workspace_is_independent` — the test opens two workspaces of one branch and changes a file in the first. The second workspace keeps the old text.
- `test_commit_makes_the_branch_and_discard_returns_to_the_last_commit` — the test commits a fix, then makes a half change and a scratch file, and calls `discard_changes`. The workspace returns to the committed text with no scratch file.
- `test_a_path_outside_the_checkout_is_refused` — the test reads and writes paths like `../outside.txt` and `/etc/...`. Both raise `RepoProviderError` and no file appears outside.
- `test_a_symlink_that_leaves_the_checkout_is_refused` — the test adds a link to a file outside the checkout. Reading it raises `RepoProviderError`.

### tests/adapters/github/test_draft_pr.py

This file proves that `open_draft_pr` pushes only the Fix branch, once, and opens a draft pull request with the right fields. It uses real git and `StubGitHubApi`.

- `remote_branch_heads(tmp_path)` — reads the bare remote and returns a map of branch name to commit.
- `draft(**fields)` — builds a `DraftPr` with test defaults. The caller can change any field.
- `committed_fix(tmp_path)` — builds a remote, a provider and a workspace with one Fix commit that is not pushed. It returns the provider and the stub API.
- `test_the_draft_pr_has_the_fix_branch_and_targets_the_source_branch` — the test opens a draft pull request. The API receives the Fix branch, the source branch as base, the draft flag, title, body and labels. The remote holds the fixed file.
- `test_only_the_fix_branch_changes_in_the_remote` — the test opens a draft pull request. Every other branch of the remote keeps its commit and the Fix branch is new.
- `test_a_second_call_for_the_same_branch_returns_the_first_url` — the test calls twice with the same branch. Both calls return one address and the API creates one pull request.
- `test_the_provider_refuses_to_push_any_other_branch` — the test tries the source branch, the default branch, a head that equals the base, and an option-like name. Each raises `RepoProviderError`, the remote keeps its commits and the API creates nothing.
- `test_a_branch_that_no_checkout_holds_cannot_be_pushed` — the test uses a Fix branch that no checkout holds. The provider raises `RepoProviderError` without the token and the API creates nothing.

### tests/adapters/github/test_existing_fix.py

This file proves how the provider decides whether a Source PR is open and whether a Fix already exists. It uses `StubGitHubApi` and a real remote.

- `LABEL` — the issue label that the tests look for. `FIX_BRANCH` is the Fix branch name `gozu/fix-GR-5`.
- `pr(**fields)` — builds a `PullRequest` with test defaults. The caller can change any field.
- `provider_with(tmp_path, pull_requests)` — makes a remote with the branches `feature-x` and the Fix branch, and returns a provider whose stub API holds the given pull requests.
- `query(**fields)` — builds a `FixQuery` with test defaults. The caller can change any field.
- `test_an_open_pr_with_this_head_is_a_source_pr` — an open pull request with the head `feature-x` exists. `has_open_pr` returns true.
- `test_a_pr_that_is_not_open_or_not_from_this_repo_is_not_a_source_pr` — the pull request has the state closed or merged, or it comes from a fork. `has_open_pr` returns false.
- `test_a_branch_without_a_pr_is_not_a_source_pr` — the only pull request has another head. `has_open_pr` returns false.
- `test_an_open_fix_pr_on_the_source_branch_is_an_open_pr` — an open Fix PR with the label targets the source branch. `find_existing_fix` returns `open_pr`.
- `test_a_pr_that_does_not_match_is_not_an_existing_fix` — the pull request has another base, another label, a fork head or a merged state. `find_existing_fix` returns nothing.
- `test_a_closed_fix_pr_whose_branch_still_exists_is_a_fix_branch` — a closed Fix PR has a branch that is still in the remote. `find_existing_fix` returns `fix_branch`.
- `test_a_closed_fix_pr_whose_branch_is_gone_is_not_a_fix` — a closed Fix PR has a branch that is not in the remote. `find_existing_fix` returns nothing.
- `test_a_closed_pr_without_the_branch_prefix_is_not_a_fix_branch` — a closed pull request has the label but its branch lacks the Fix prefix. `find_existing_fix` returns nothing.
- `test_an_open_pr_wins_over_a_fix_branch` — one closed Fix PR with a live branch and one open Fix PR exist. `find_existing_fix` returns `open_pr`.
- `test_the_repository_name_is_compared_without_case` — the pull request head repository is `Acme/App`. `has_open_pr` for `acme/app` returns true.

### tests/adapters/jira/support.py

This file holds the helpers that the Jira tests share. It exists so every test builds the tracker in the same way.

- `API_TOKEN` — a fake Jira API token that the file builds from pieces.
- `SEARCH` — the method and path of the Jira search route.
- `FIELDS` — the method and path of the Jira field list route.
- `make_tracker(server, email, **settings)` — builds a real `JiraTracker` that talks to the stub server. The default email is `bot@example.invalid`. The project keys are `SEC` and `OPS`. Extra settings go to `JiraSettings`. It returns the tracker.

### tests/adapters/jira/test_gateway.py

This file proves that `resolve_api_base` builds the gateway address from the cloud id of the site. It is separate because it tests one function.

- `test_the_gateway_url_comes_from_the_cloud_id_of_the_site` — the site answers with a cloud id. The function returns the Atlassian gateway address with that id.
- `test_a_site_that_gives_no_cloud_id_is_an_error` — the site answers 404. The function raises `TrackerError`.

### tests/adapters/jira/test_settings.py

This file proves that `JiraSettings` refuses values that could change the search text of Jira.

- `test_the_settings_refuse_a_project_key_that_could_change_the_search` — the test gives a key with quote text, a lower case key and an empty list. The settings raise a validation error.
- `test_the_settings_refuse_an_eligible_label_that_could_change_the_search` — the test gives labels with a quote, a space, an empty text or a backslash. The settings raise a validation error.

### tests/adapters/jira/test_connection.py

This file proves how the Jira tracker connects. It checks the sign-in method, the safety of errors and the handling of answers in a wrong shape.

- `EMAIL` — the email `bot@example.invalid` of the test bot in the Jira credentials.
- `authorization_of(server)` — returns the `Authorization` header of the first request that the server saw.
- `test_an_email_and_a_token_use_basic_authentication` — the tracker has an email and a token. The first request has a Basic header that holds the email and the token.
- `test_a_token_with_no_email_is_a_bearer_token` — the tracker has a token and no email. The first request has a Bearer header.
- `test_an_error_names_the_status_and_never_holds_a_credential` — the server answers 401 and repeats the token in its message. The tracker raises `TrackerError` with the status and without the token or its encoded form.
- `test_a_reply_that_is_not_json_is_an_error` — the search answer is not JSON. The tracker raises `TrackerError`.
- `test_a_server_that_is_down_is_an_error_without_the_token` — the test stops the server before the call. The tracker raises `TrackerError` without the token.
- `test_a_redirect_never_carries_the_credentials_to_another_host` — the server answers a redirect to a second server. The tracker raises `TrackerError` and the second server sees no request.
- `test_the_credentials_do_not_show_in_repr_or_in_a_dump` — the test builds `JiraCredentials`. The token is not in its `repr` or its JSON dump.
- `test_the_adapter_refuses_a_site_that_is_not_https` — the test gives `http`, `file`, `ftp` and bare addresses. Both `JiraTracker` and `resolve_api_base` raise `TrackerError`.
- `test_a_search_answer_in_an_unexpected_shape_is_a_tracker_error` — the search answer is empty, has an issue with no key, has an issue with no fields, or is a list. The tracker raises `TrackerError`.
- `test_a_status_answer_in_an_unexpected_shape_is_a_tracker_error` — the issue answer has no fields, no status or an empty status. `set_status` raises `TrackerError`.
- `test_a_comment_page_in_an_unexpected_shape_is_a_tracker_error` — the comment list has no `comments` entry. `add_comment` raises `TrackerError`.

### tests/adapters/jira/test_open_tickets.py

This file proves that `open_tickets` builds Gozu Tickets from Jira issues. It checks the search text, the paging, the skip rules and the use of the Details list and the custom fields.

- `EXPECTED_JQL` — the search text that the tracker must send. It lists the projects, the eligible label, a not done status, no assignee and an order by key.
- `serve(server, *pages)` — sets the field list route to an empty list and the search route to the given pages in order.
- `test_a_gozurion_ticket_becomes_a_ticket_with_the_exact_branch` — one Gozurion issue becomes one ticket. The key, repository, file, line, severity, branch, finding and issue label match the issue.
- `test_the_ticket_carries_every_label_so_the_failed_fix_marker_shows` — the issue has the marker label of a Failed Fix. The ticket holds all labels of the issue.
- `test_the_search_asks_for_open_unassigned_tickets_with_the_eligible_label` — the tracker searches. The body of the request has the expected search text.
- `test_the_eligible_label_comes_from_the_settings` — the settings name the label `fix-me`. The search text uses that label.
- `test_every_page_of_the_search_is_read` — the first page has a next page token. The tracker reads both pages in order and sends the token with the second request.
- `test_a_ticket_that_is_not_a_finding_of_one_line_is_skipped` — a roll-up issue, an issue with no line and an issue with branch `unknown` are in the answer. The tracker returns only the valid ticket.
- `test_a_scanner_that_gives_a_plain_path_works_too` — the component is a plain path with no prefix. The ticket file equals that path.
- `test_a_bullet_in_the_finding_text_never_beats_the_details_list` — a bullet that says `Line: 99` comes before the Details list. The ticket line comes from the Details list.
- `test_a_path_with_a_colon_keeps_its_folders` — the component path holds a colon. The ticket file keeps the whole path.
- `test_a_line_that_a_number_field_gives_as_a_float_works` — the custom line field is the number 12.0. The ticket line is 12 and the severity comes from a field with a value record.
- `test_the_custom_fields_of_gozurion_fill_the_ticket_when_the_details_lack_them` — the Details lack the file, line and severity, and custom fields hold them. The ticket takes them from the custom fields. The search asks only for the labels, the description and the three custom fields.

### tests/adapters/jira/test_comments.py

This file proves that `add_comment` posts a comment with a hidden marker and never posts the same comment twice.

- `COMMENTS`, `LIST`, `POST` and `TEXT` — the comment path, the list route, the post route, and the two line text of the comment.
- `no_comments()` — returns the answer of an empty comment list.
- `sent(server)` — returns the comment posts that the server saw.
- `comment_with(properties)` — builds one comment record with an id and the given properties.
- `test_a_comment_is_posted_with_its_text_and_a_hidden_marker` — the tracker posts a comment. The body has one paragraph for each line of text. A property with key `veil` holds a marker, and the text is not in that property.
- `test_the_same_comment_is_not_posted_twice` — the list already holds a comment with the marker of this text. The tracker posts nothing more.
- `test_a_different_text_is_posted_even_when_another_marker_exists` — the list holds a marker for another text. The tracker posts the new text.
- `test_a_person_comment_with_the_same_words_does_not_count_as_a_marker` — the list holds a comment with no marker. The tracker still posts.
- `test_a_marker_on_a_later_page_of_comments_is_found` — the marker is on the second page of the list. The tracker finds it and posts nothing. The last read asks for `startAt` 1 and the properties.

### tests/adapters/jira/test_changes.py

This file proves that `add_label` and `set_status` change a ticket safely. It checks the transition choice, the rule against closing a ticket and the refusal of bad keys and labels.

- `ISSUE`, `EDIT`, `TRANSITIONS` and `DO_TRANSITION` — the routes for the issue read, the issue edit, the transition list and the transition post.
- `transition(identifier, target, category)` — builds one transition record with an id, a name, a target status and a status category. The default category is `indeterminate`.
- `serve_status(server, current, transitions)` — sets the routes so the ticket has the current status and offers the given transitions.
- `sent(server, route)` — returns the requests that the server saw for one route.
- `test_add_label_asks_jira_to_add_the_label_without_a_read_first` — the test adds a label twice. Each request is a `PUT` with an add update, and the tracker reads nothing first.
- `test_set_status_makes_the_transition_that_ends_in_that_status` — the server offers two transitions. The tracker posts the one that ends in `In Review`.
- `test_set_status_does_nothing_when_the_ticket_is_already_in_that_status` — the ticket already has the status. The tracker posts no transition.
- `test_set_status_uses_the_status_name_of_the_settings` — the settings map `In Review` to `Code Review`. The tracker posts the transition to `Code Review`.
- `test_the_adapter_never_closes_a_ticket` — the only matching transition ends in a done category. The tracker raises `TrackerError` and posts nothing.
- `test_a_status_that_the_workflow_does_not_offer_is_an_error` — no transition ends in the wanted status. The tracker raises `TrackerError` and posts nothing.
- `test_a_key_that_is_not_a_ticket_key_is_refused_before_any_request` — the key is a path trick, has lower case letters or is empty. Both methods raise `TrackerError` and the server sees no request.
- `test_a_label_that_jira_cannot_hold_is_refused` — the label has a space, a quote or is empty. `add_label` raises `TrackerError` and the server sees no request.

### tests/adapters/openai/test_http_api.py

This file proves that `HttpOpenAIApi` sends the right requests to a stub server and reads the replies. It also proves the rules for errors, retries and key safety.

- `API_KEY` — a fake OpenAI key that the file builds from pieces.
- `RESPONSES`, `INPUT` and `TOOLS` — the route of the responses call, a one message input and a one tool list.
- `api_for(server, **options)` — builds an `HttpOpenAIApi` with the fake key and the stub server address. Extra options go to the adapter.
- `create(server, **options)` — builds the adapter and calls `create_response` with the model `cheap-model`, `INPUT` and `TOOLS`. It returns the reply.
- `test_the_request_has_the_model_the_items_the_tools_and_no_storage` — the adapter sends a call. The body holds the model, the input, the tools and `store` set to false. The header is a bearer key.
- `test_the_function_calls_and_the_tokens_come_from_the_reply_and_other_items_are_ignored` — the reply holds a reasoning item, a message and two function calls. The adapter returns only the two calls and the total of 120 tokens.
- `test_the_tokens_are_the_sum_when_the_reply_gives_no_total` — the usage has input and output counts but no total. The token count is 75.
- `test_a_reply_with_no_usage_is_an_error_and_never_zero_tokens` — the reply has no usage. The adapter raises `ModelClientError` that names usage and cannot be retried.
- `test_an_incomplete_reply_still_gives_its_calls_and_tokens` — the status is `incomplete`. The adapter still returns the call and 120 tokens.
- `test_a_failed_reply_is_an_error_that_says_if_a_retry_can_help` — the reply has the status `failed` with a code. The adapter raises `ModelClientError` with the code and no key. A server error and a rate limit can be retried and an invalid prompt cannot.
- `test_an_http_error_names_the_status_hides_the_key_and_says_if_a_retry_can_help` — the server answers 429, 500, 502, 503, 400 or 401. The error names the status and hides the key. The codes 429 and 5xx can be retried and 400 and 401 cannot.
- `test_a_429_that_says_the_quota_is_gone_is_not_worth_a_retry` — the 429 body says `insufficient_quota`. The error cannot be retried.
- `test_the_tools_are_not_changed_on_the_way_to_the_api` — the adapter sends the tools. The body holds the same tool list.
- `test_a_server_that_is_down_is_a_retryable_error_without_the_key` — the test stops the server before the call. The adapter raises a `ModelClientError` that can be retried and holds no key.
- `test_a_call_that_takes_longer_than_the_time_out_is_a_retryable_error` — the server waits 0.6 seconds and the time out is 0.1 seconds. The adapter raises a `ModelClientError` that can be retried.
- `test_a_redirect_never_carries_the_key_to_another_host` — the server answers 307 to a second server. The adapter raises `ModelClientError` and the second server sees no request.
- `test_the_adapter_refuses_a_url_that_is_not_https` — the test gives `http`, `file` and bare addresses. The adapter raises `ModelClientError`.
- `test_a_reply_in_an_unexpected_shape_is_a_tracker_style_error` — the reply has no output, a text output, a call with no name, arguments that are not text, or is a list. The adapter raises `ModelClientError`.
- `test_the_key_does_not_show_in_repr` — the test builds the adapter. The key is not in its `repr`.

### tests/adapters/openai/test_client.py

This file proves that `OpenAIModelClient` turns Engine messages into API items and API replies into Engine replies. The last test runs the whole Engine with the real client and a stub API.

- `TOOLS` and `MESSAGES` — one tool definition for `read_file` and a system and a user message.
- `client_with(*replies)` — builds a `StubOpenAIApi` with the replies and a client on top of it. It returns both.
- `test_the_reply_has_each_call_with_the_id_of_the_api_and_the_tokens_it_counted` — the API returns two calls and 137 tokens. The client returns two tool calls with the API ids, parsed arguments and 137 tokens.
- `test_the_model_name_and_the_tools_go_to_the_api_in_the_responses_shape` — the client sends a call. The API receives the model name and each tool in the function form with `strict` set to false.
- `test_the_conversation_goes_to_the_api_as_items_and_each_answer_names_its_call` — the conversation holds two tool calls and two answers. The API receives function call items and function call output items with the matching call ids.
- `test_arguments_that_are_not_a_json_object_become_a_call_with_no_arguments` — the arguments are broken JSON, a list, `null`, a text or empty. The client returns a call with empty arguments.
- `test_a_reply_with_no_call_has_no_tool_calls_and_still_counts_tokens` — the API returns no call and 55 tokens. The client returns an empty call list and 55 tokens.
- `test_a_tool_message_that_answers_no_call_is_a_clear_error_and_nothing_is_sent` — a tool message answers an unknown call. The client raises `ModelClientError` that says so, it cannot be retried, and the API receives no request.
- `test_an_error_of_the_api_reaches_the_caller_unchanged` — the API raises a `ModelClientError`. The client raises the same error object.
- `test_the_engine_fixes_a_ticket_with_the_real_client_and_counts_the_api_tokens` — the Engine runs with the real client and a stub API that edits a file and finishes. The report shows the ticket fixed with 33 tokens, the Fix PR holds the fixed file, and the second request answers only the first call.

### tests/fakes/__init__.py

This file lets a test import the fakes and the helpers from one place. It has no functions.

- It lists `FakeModelClient`, `FakeRepoProvider` and `FakeTracker`.
- It also lists the helper functions `edit_file`, `finish`, `list_dir`, `make_ticket`, `read_file` and `search`.

## Things to know

- The stub server answers a path with no route as a 404 and does not fail the test. A test that forgets a route sees an adapter error, not a clear message.
- A person wrote the Jira and OpenAI answers by hand from the public documents. Nobody recorded them from a live call. Only `github_fixtures.py` has no such note in its header.
- Every adapter has a redirect test. The adapter must refuse to send its Credential to a second host. The test proves it when the second stub server sees no request.
- The files `support.py` and `test_http_api.py` build the fake keys and tokens from pieces in `support.py` and `test_http_api.py`. The tests check that these values never show in errors, `repr` output, git configuration or JSON dumps.
- `FakeRepoProvider.open_draft_pr` refuses the same pushes as the real provider. It refuses a head without the Fix prefix and a head equal to the base. This keeps the Engine tests honest about which branches the Engine may push.
- The snapshot has no `tests/adapters/settings` folder. This part does not cover a test of the YAML settings.
