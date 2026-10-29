# The Jira adapter (the real tracker)

An adapter is a part that talks to an outside service. This adapter talks to Jira Cloud. It gives the Engine its Gozu Tickets, and it writes comments, labels and statuses back to Jira. Jira words, search text and label names live in this adapter and nowhere else. ADR 0008 gives the reasons.

## The flow

1. A Shell builds `JiraSettings` (where the tickets are) and `JiraCredentials` (who the agent is). A Shell is a way to run the Engine. A Shell can call `resolve_api_base` in `gateway.py` once. This finds the gateway URL that a scoped token needs.
2. The Shell makes a `JiraTracker`. Its `__init__` makes a `JiraHttp`. `JiraHttp` refuses a URL that is not https, and it builds the one `Authorization` header. Part 07 (the shared HTTP code) does the real network call.
3. The Engine (part 02) calls `open_tickets`. It is a method of the Tracker interface (part 04).
4. `open_tickets` first calls `_custom_field_ids`. This asks Jira for the list of fields. It keeps the ids of the three custom fields that Gozurion fills. A site can have none of them.
5. `open_tickets` builds the search text with `_jql`. The search asks for tickets with a project key from the settings. A ticket must carry the eligible label. It must not be in the Done category. It must have no assignee. It sorts them by key.
6. `open_tickets` sends the search in pages of 100. It follows `nextPageToken` until Jira gives no token. It asks for the fields `labels`, `description` and the custom fields.
7. For each Jira issue, `open_tickets` calls `ticket_from_issue` in `issue_parser.py`. This function reads the description with `details_of` and `finding_text` from `adf.py`. Only the list below the heading `Details` counts.
8. `ticket_from_issue` reads the custom fields with `_custom_text`. A value from the Details list wins. A custom field fills only a detail that the list does not have.
9. `ticket_from_issue` cuts the project from the component with `_path_of`. This gives the file path.
10. `ticket_from_issue` gives `None` when the issue is not a finding of one line. It does so for a roll-up ticket. It does so when the line, the repository, the severity or the finding text is missing. It also does so when the branch is missing or is `unknown`. `open_tickets` skips these. Otherwise `ticket_from_issue` builds a `Ticket` (part 04).
11. The Engine calls `add_label` for the Failed Fix label. `add_label` checks the key and the label, then asks Jira to add the label. Jira keeps one copy, so a repeat gives the same state.
12. The Engine calls `set_status` to move a ticket, for example to `In Review`. `set_status` maps the name through the settings. It reads the current status. If the ticket is already there, it stops. Otherwise it finds the transition that ends in that status.
13. `set_status` raises `TrackerError` when the workflow has no such transition. It also raises `TrackerError` when the status is in the Done category. The adapter never closes a ticket.
14. The Engine calls `add_comment`. `add_comment` makes a marker from the text, a hash of 32 characters. It asks `_has_marker` to read the comments of the ticket. If a comment already has the marker, it stops.
15. If no comment has the marker, `add_comment` posts the comment. It builds the comment body with `comment_body`. It stores the marker in a hidden comment property. Jira does not show the property.
16. Every answer that has a wrong shape raises `TrackerError`. It never raises a raw `KeyError`.

## Files

### src/veil/adapters/jira/gateway.py

This file finds the URL that a Shell must use for the REST calls. It is its own file because a Shell calls it one time, before it makes the tracker.

- `resolve_api_base(site_url)` — asks the Jira site for its cloud ID, with no credentials. In: the site URL. Out: the gateway URL, which is the gateway constant, a slash and the cloud ID. It raises `TrackerError` when the site gives no cloud ID. A Shell calls it.

### src/veil/adapters/jira/models/jira_credentials.py

This file holds the record of the Credential that the Shell gives the adapter. It is separate from the settings because the credentials never come from settings.

- `JiraCredentials` — a pydantic model, which is a checked record. It is frozen, so nobody can change it. It hides input values in errors.
  - `email` — the email of the account. It is optional. With an email, the adapter uses basic authentication.
  - `api_token` — the token, as a `SecretStr`, which hides its value when printed. With no email, the adapter uses it as a bearer token.

### src/veil/adapters/jira/constants/http.py

This file holds the paths and numbers for the Jira REST calls.

- `SEARCH_PATH` — the path of the issue search, `/rest/api/3/search/jql`.
- `FIELD_PATH` — the path of the list of fields, `/rest/api/3/field`.
- `ISSUE_PATH` — the path of one issue, `/rest/api/3/issue`.
- `TRANSITIONS_SEGMENT` — the word `transitions`. It goes after the issue key in a path.
- `COMMENT_SEGMENT` — the word `comment`. It goes after the issue key in a path.
- `PAGE_SIZE` — 100. It is the page size of the search and of the comment list.
- `TENANT_INFO_PATH` — `/_edge/tenant_info`. Jira gives the cloud ID of a site here, with no credentials.
- `GATEWAY_URL` — `https://api.atlassian.com/ex/jira`. A scoped token works only through this gateway. The cloud ID follows it.

### src/veil/adapters/jira/constants/patterns.py

This file holds the patterns that keep a key or a label from changing a URL or a search.

- `ISSUE_KEY` — a ticket key. It is a capital letter, then capital letters, digits or `_`, a dash and a number.
- `SAFE_LABEL` — a label. It has no space, no quote and no backslash.
- `PROJECT_KEY` — a project key. It is a capital letter, then capital letters, digits or `_`.

### src/veil/adapters/jira/constants/workflow.py

This file holds the words of the Jira workflow that the adapter uses.

- `DONE_CATEGORY` — the word `done`. It is the status category of a closed ticket. The adapter never moves a ticket into it.
- `DEFAULT_ELIGIBLE_LABEL` — the word `veil-eligible`. It is the label that marks a ticket that the Engine may fix. A setting can change it.
- `COMMENT_PROPERTY_KEY` — the word `veil`. It is the key of the hidden comment property that holds the marker.

### src/veil/adapters/jira/constants/details.py

This file holds the names that Gozurion writes in a ticket. Gozurion is the part that creates the tickets from scan findings.

- `DETAIL_REPOSITORY` — the line name `Repository`.
- `DETAIL_COMPONENT` — the line name `Component`.
- `DETAIL_LINE` — the line name `Line`.
- `DETAIL_SEVERITY` — the line name `Severity`.
- `DETAIL_BRANCH` — the line name `Branch`.
- `UNKNOWN_BRANCH` — the word `unknown`. Gozurion writes it when the scan knew no branch.
- `COMPONENT_SEPARATOR` — the colon. A Sonar component is `project:path`.
- `CUSTOM_FIELD_COMPONENT` — the custom field name `SonarQube Component`.
- `CUSTOM_FIELD_LINE` — the custom field name `SonarQube Line`.
- `CUSTOM_FIELD_SEVERITY` — the custom field name `SonarQube Severity`.
- `DETAILS_HEADING` — the word `Details`. It is the heading above the list of details. Only the list below it counts.
- `CUSTOM_FIELD_NAMES` — a map from a detail name (component, line, severity) to its custom field name. The tracker and the parser both read it.

### src/veil/adapters/jira/models/jira_settings.py

This file holds the settings of the adapter. They are not secret. It is separate from the credentials so that a person can store settings in a file.

- `JiraSettings` — a pydantic model. It is frozen.
  - `site_url` — the URL of the Jira site. The tracker uses it when the Shell gives no gateway URL.
  - `project_keys` — a tuple of project keys. It needs at least one key.
  - `eligible_label` — the label that a ticket needs. The default is `veil-eligible`.
  - `status_names` — a map from the Engine name of a status to the workflow name, for example for `In Review`. It is empty by default.
- `_safe_project_keys(cls, keys)` — a check on `project_keys`. It raises an error when a key does not match `PROJECT_KEY`. In: the tuple of keys. Out: the same tuple. Pydantic calls it.
- `_safe_label(cls, label)` — a check on `eligible_label`. It raises an error when the label does not match `SAFE_LABEL`. In: the label. Out: the same label. Pydantic calls it.

### src/veil/adapters/jira/http_client.py

This file makes the Jira REST calls with JSON. It is its own file so that the tracker and the gateway share one place that holds the authorization header. Part 07 (the shared HTTP code) does the real work.

- `JiraHttp` — the class that calls the Jira REST API. It puts the credentials in the `Authorization` header and nowhere else.
- `JiraHttp.__init__(api_base, credentials)` — refuses a base URL that is not https. It removes a closing slash. With an email, it makes a basic header and keeps the token and the encoded value as secrets to hide. With a token alone, it makes a bearer header. With `None`, it sends no header. The tracker and the gateway call it.
- `JiraHttp.call(method, path, params, body, shape)` — sends one request and gives back the decoded JSON. In: the method, the path, optional query values, an optional body and an optional kind (for example `dict` or `list`). Out: the reply. It raises `TrackerError` when the reply is not of the kind that the caller asked for. The code defines it with two typed forms, called overloads, that only help type checkers. One real function does the work.

### src/veil/adapters/jira/adf.py

This file reads and writes Atlassian Document Format (ADF). Jira sends rich text as JSON in this format. It is its own file because it only handles text shapes and knows nothing about tickets.

- `text_of(node)` — gives the plain text of a node and all its children. In: one ADF node. Out: a string. The other functions of this file call it.
- `_walk(node)` — visits a node and then each child, deep into the tree. In: one node. Out: the nodes one by one. `finding_text` calls it.
- `finding_text(description)` — gives the text of the finding. It takes the first expand block if one exists, because Gozurion puts the full text there when it cut the first paragraph short. Otherwise it takes the first paragraph. It gives an empty string when it finds neither. `ticket_from_issue` calls it.
- `details_of(description)` — reads the `Name: value` lines of the bullet list that follows the `Details` heading. It reads only that list. The first value of a name wins. In: the description. Out: a map of names to values. `ticket_from_issue` calls it.
- `comment_body(text)` — builds an ADF document for a comment. Each line that is not empty becomes one paragraph. In: the text. Out: the document. `add_comment` calls it.

### src/veil/adapters/jira/issue_parser.py

This file turns one Jira issue into a `Ticket`. It is its own file so that the rules for a finding are in one place.

- `ticket_from_issue(issue, custom_ids)` — builds a `Ticket` from an issue, or gives `None` when the issue is not a finding of one line. In: the issue and the map of custom field names to ids. Out: a `Ticket` or `None`. It gives `None` when the description is not a document, or when the file, the line, the repository, the severity or the finding text is missing. It also gives `None` when the line is not a whole number, the branch is missing or the branch is `unknown`. The tracker calls it for each issue.
- `_custom_text(value)` — gives the text of a custom field value. An option field gives an object, so it reads the `value` or the `name` of it. A number field can give 12.0, so it turns a whole float into an integer. An empty value gives an empty string.
- `_path_of(component)` — gives the file path from a Sonar component. It cuts the text before the first colon. If that text has a slash or a backslash, it is a folder and not a project, so the whole component stays.

### src/veil/adapters/jira/tracker.py

This file is the real tracker. It has the same methods as the Tracker interface (part 04). It is the one file that knows the search text, the label rules and the status rules.

- `_expected_shape(what)` — a helper block. It turns a missing key, a wrong kind or a bad value in a Jira answer into a `TrackerError` that names what Jira gave. In: a short name of the answer. The methods of the tracker use it.
- `JiraTracker` — the class of the real tracker. It satisfies the Tracker interface of the Engine.
- `JiraTracker.__init__(settings, credentials, api_base)` — keeps the settings and makes a `JiraHttp`. It uses the gateway URL when the Shell gives one. Otherwise it uses `site_url`.
- `JiraTracker.open_tickets()` — gives the list of Gozu Tickets that the Engine may fix. It reads the custom field ids, searches page by page and builds a `Ticket` for each finding. It skips an issue that gives `None`. Out: a list of `Ticket`. The Engine calls it.
- `JiraTracker.add_comment(key, text)` — posts a comment with a hidden marker. The marker is the first 32 characters of the SHA-256 hash of the text. It does nothing when a comment already has that marker. It refuses a bad key. The Engine calls it.
- `JiraTracker._has_marker(key, marker)` — reads the comments of a ticket, 100 at a time, with their properties. It gives true when a comment has the `veil` property with this marker. It gives false when it reaches the end. `add_comment` calls it.
- `JiraTracker.add_label(key, label)` — asks Jira to add a label. It refuses a bad key. It refuses a label that has a space, a quote or a backslash. A repeat gives the same state. The Engine calls it.
- `JiraTracker.set_status(key, status)` — moves a ticket to a status. It maps the name through `status_names`. It compares names with no regard to capital letters. It does nothing if the ticket is there. It raises `TrackerError` when no transition ends in the status. It raises `TrackerError` when the status is in the Done category. Otherwise it makes the transition. The Engine calls it.
- `JiraTracker._check_key(key)` — raises `TrackerError` when the key does not match `ISSUE_KEY`. The three write methods call it.
- `JiraTracker._custom_field_ids()` — asks Jira for all fields. It gives a map from the field name to the field id for the three Gozurion fields. `open_tickets` calls it.
- `JiraTracker._jql()` — builds the search text in JQL, the search language of Jira. It quotes each project key and the eligible label. It asks for no Done category and no assignee. `open_tickets` calls it.

## Things to know

- The adapter never closes a ticket. `set_status` raises `TrackerError` for a transition whose status is in the `done` category. It makes this check before the transition call.
- The adapter does not add the eligible label. A person or a Jira rule adds it. A ticket without the label never reaches the Engine.
- A repeat call is safe. `add_label` relies on Jira to keep one copy. `set_status` does nothing when the status matches. `add_comment` skips a text whose marker exists.
- The marker is a hash of the text only. If a person removes the first comment, the adapter does not post that text again. A person who can edit comments can copy the marker.
- The status check and the transition are two calls. Two runs at the same time can both try the transition. The adapter has no retry for a rate limit answer.
- The settings refuse a project key or a label that could change the search text. The tracker refuses a ticket key or a label that could change a URL. The tests use replayed Jira answers and no live site.
