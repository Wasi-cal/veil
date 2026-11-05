# Settings

veil reads its settings from one file in the repo: `.gozu/jira-to-pr.yml`. The file is optional for most settings. Two settings have no default and you must set them: `jira_site_url` and `jira_project_keys`.

Each key in the file is one setting. A key that is not in this list fails the run. A value of the wrong type or outside its range fails the run. A value that looks like a secret fails the run. The message names the setting and never repeats the value.

The safety rules are code and are not settings. You cannot turn them off. They are: never merge, never touch the default branch, never read, list or edit anything in `.github/`, no shell and no network for the model.

## The fix loop

| Setting | Default | Range | What it does |
|---|---|---|---|
| `cheap_model` | `gpt-6-luna` | any name | The model for the first attempt. |
| `strong_model` | `gpt-6.1-terra` | any name | The model for the second attempt. |
| `cheap_reasoning_effort` | not set | `none`, `low`, `medium`, `high`, `xhigh`, `max` | How much the cheap model reasons before each step. A lower level costs less and is faster, because reasoning tokens are billed as output. It may fix fewer hard tickets. The strong model keeps its own default. Not set leaves the choice to the model. A model that does not take the level makes the API refuse the call. |
| `max_attempts` | 2 | 1 to 2 | The attempts for one ticket. With 1, the strong model never runs. |
| `step_cap` | 25 | 1 to 100 | The most tool calls in one attempt. |
| `tool_result_max_bytes` | 8192 | 256 to 65536 | The most bytes of one tool result that the model sees. |
| `read_file_max_lines` | 300 | 1 to 2000 | The most lines that one read gives. |
| `search_max_matches` | 50 | 1 to 500 | The most matches that one search gives. |
| `explanation_max_sentences` | 3 | 1 to 10 | The most sentences in each of the three parts of the explanation. |
| `extra_refused_read_patterns` | none | a list | Files that the model may not read, in addition to the built-in list. |
| `ticket_token_cap` | 100000 | 1 to 5000000 | The most tokens that one ticket may use, over all its attempts. A ticket that uses its cap becomes a Failed Fix. The run goes on. |

## Grouping and names

| Setting | Default | Range | What it does |
|---|---|---|---|
| `branch_prefix` | `veil/fix-` | a safe prefix | The start of the name of a Fix branch. |
| `severity_map` | see below | words to buckets | Which bucket each severity word goes to: `low`, `medium` or `high`. The bucket sets only the order of the PRs: High first. A word that you name changes. The other words keep their default. |
| `model_prices` | list of default prices | up to 50 models | The price of each model in US dollars for 1 million tokens, for the cost in the run summary. Write `model: {input: 0.10, cached_input: 0.01, output: 0.50}`. A price here adds a model or replaces its default price. |
| `failed_fix_label` | `veil-failed-fix` | one word | The label on a ticket that has a Failed Fix. |
| `in_review_status` | `In Review` | a status name | The status that a ticket gets after a PR opens. The Jira workflow must have it. |

The default severity map: `BLOCKER`, `CRITICAL`, `HIGH` go to `high`. `MAJOR` and `MEDIUM` go to `medium`. `MINOR`, `INFO` and `LOW` go to `low`.

## Jira and the credentials

| Setting | Default | What it does |
|---|---|---|
| `jira_site_url` | none | The https address of your Jira site. You must set it. No user name or password may be in it. |
| `jira_project_keys` | none | The Jira project keys to search. You must set at least one. |
| `eligible_label` | `veil-eligible` | The label that a ticket needs. An empty text turns the check off. |
| `jira_email_env` | `JIRA_EMAIL` | The name of the variable that holds the Jira email. |
| `jira_token_env` | `JIRA_API_TOKEN` | The name of the variable that holds the Jira token. |
| `openai_key_env` | `OPENAI_API_KEY` | The name of the variable that holds the OpenAI key. |

A variable name has capital letters, digits and underscores. It may not start with `GITHUB_`, `ACTIONS_`, `RUNNER_`, `INPUT_` or `GOZU_`. Two credentials may not share one variable.

## Triggers

| Setting | Default | What it does |
|---|---|---|
| `schedule_enabled` | `false` | Allow runs from the `schedule` event. |
| `on_demand_enabled` | `true` | Allow runs from `workflow_dispatch`. |
| `event_enabled` | `true` | Allow runs from `repository_dispatch`. |
| `pull_request_enabled` | `false` | Allow runs from `pull_request`. A run sees only the tickets of the branch of that PR. A PR from a fork never runs. |

The cron time is in the workflow file, not here.

## An example

```yaml
jira_site_url: "https://yourco.atlassian.net"
jira_project_keys: ["SEC"]
ticket_token_cap: 30000
```
