# The real Jira tracker

The real tracker is `JiraTracker` in `veil/adapters/jira/`. It satisfies the `Tracker` interface of the Engine (ticket GR-19). Jira statuses, JQL and label names live in this adapter and nowhere else.

## What we decided

- **One module, no extra seam.** The adapter has one real implementation, so it has no `JiraApi` interface. Tests run the real HTTP code against a local stub server that replays Jira answers.
- **Which tickets.** The search asks for tickets of the project keys. A ticket must carry the eligible label. It must not be in the done category. It must have no assignee. The eligible label is the setting `eligible_label`. Its default is `veil-eligible`. The Shell builds the Jira settings from the settings of the run with `JiraSettings.from_settings`. A person or a Jira rule adds it. Gozurion does not add it.
- **Reading a ticket.** Gozurion writes the repository, the component, the line, the severity and the branch in a Details list. The adapter reads only the list below the Details heading. A bullet in the text of the finding never wins. A site can move the component, the line and the severity into custom fields, so the adapter reads those too. A number field can give 12.0, and an option field gives an object. The adapter reads both. The exact branch comes from the Details list. The label `branch-...` is lower case and not exact. A Sonar component is `project:path`, so the file is the text after the colon. A path that has a folder before its colon keeps all of it.
- **Tickets that are not findings.** A roll-up ticket, a ticket with no line and a ticket with an unknown branch give no Engine ticket. The adapter skips them.
- **Labels.** `add_label` asks Jira to add the label. Jira keeps one copy, so a repeat gives the same state. The Failed Fix label is the constant of the Engine. It is not a setting of the adapter.
- **Status.** `set_status` reads the status. If the ticket is there, it does nothing. If not, it makes the transition that ends in that status. The Engine says the name of the setting `in_review_status`. The default is `In Review`. A workflow that names the status another way changes that setting.
- **Never closed.** The adapter refuses a transition that ends in the done category. It raises an error.
- **Comments.** Each comment has a hidden marker. The marker is a hash of the text in a comment property. Jira does not show it. The adapter reads the properties of the comments and skips a comment whose marker exists.
- **Https only.** The adapter refuses a site URL that is not https. Only local hosts may use http, so that tests can run against a local server.
- **Answers in a wrong shape.** A missing key or a wrong kind of value in an answer raises `TrackerError`. It never raises a raw `KeyError`.
- **Shared code.** Both adapters call `veil/adapters/json_http.py`. It builds the request, hides credential values in errors and follows no redirect. A contract keeps that shared code free of any adapter.
- **Metadata cache.** The tracker takes an optional `MetadataCache` for the custom field ids and the transitions of a project, an issue type and a status. The default keeps nothing. When Jira calls a move with a cached transition not valid, the tracker reads Jira once and tries again. `TrackerError` carries the HTTP status for this. ADR 0012 describes the Redis version.
- **Credentials.** The Shell passes an email and a token as `SecretStr` values, or a token alone for a bearer token. They never come from settings. They go in one header. The adapter never follows a redirect. It hides them in every error.
- **The gateway.** A scoped token works only through the cloud ID gateway of Atlassian. `resolve_api_base` finds that URL. A Shell calls it once and passes the result in.
- **Errors.** The adapter raises `TrackerError` (in `engine/errors`). `run()` still stops on it, as ADR 0005 accepts for the repo provider.
- **A key and a label are data.** The adapter refuses a ticket key or a label that could change a URL or a search. The settings refuse a project key or a label that could change the JQL.

## What we accept for now

- The test answers follow the Jira Cloud REST documentation and the text that Gozurion writes. They are not recorded from a live site. See the manual check below.
- A comment with the same text gives the same marker. If a person deletes the first comment, the adapter does not post it again.
- The status check and the transition are two calls. Two runs at the same time can both try the transition. The second call fails with an error from Jira.
- The adapter does not retry after a rate limit answer (429). The run stops.
- A workflow with no transition to the status gives an error. The run stops.
- The adapter reads the text of the paragraph, the expand block and the bullet lists of a description. It flattens other nodes.
- No shared tests run on both the fake tracker and the real one. The real tracker has its own tests with the same rules.
- The hidden marker is a hash of the text. A person who can edit comments can copy it.
- A ticket that a person edits so that the Details list changes can stop being a finding. The adapter then skips it.

## Manual check against a test project

No person did this check yet. Do it before the first real run:

1. Make a Jira project with a workflow that has an `In Review` status.
2. Let Gozurion make one ticket, or copy its format. Add the label `veil-eligible`.
3. Call `open_tickets` and check that the ticket has the right repository, file, line, severity and branch.
4. Call `add_comment` twice with the same text. Check that Jira shows one comment.
5. Call `set_status` for `In Review` twice. Check that the ticket moves once.
6. Try a status in the done category. Check that the adapter refuses.
7. Call `add_label` with the Failed Fix label. Check that the next `open_tickets` shows it.
