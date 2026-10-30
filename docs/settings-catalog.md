# Settings catalog

The declaration of the settings makes this file. Do not edit it.
Run `python docs/settings/build.py` to make it again.

Each setting has a default in code. Four layers can change it. A later layer wins:
defaults, org settings, repo settings, per-run overrides.
Settings hold no secrets. The safety rules are code and are not settings.

| Key | Type | Default | Minimum | Maximum | Repo rule | Read by |
| --- | --- | --- | --- | --- | --- | --- |
| `cheap_model` | str | gpt-6-luna | - | - | free | engine |
| `strong_model` | str | gpt-6.1-terra | - | - | free | engine |
| `max_attempts` | int | 2 | 1 | 2 | lower | engine |
| `step_cap` | int | 25 | 1 | 100 | lower | engine |
| `diff_limit` | int | 200 | 0 | 2000 | lower | engine |
| `tool_result_max_bytes` | int | 8192 | 256 | 65536 | lower | engine |
| `read_file_max_lines` | int | 300 | 1 | 2000 | lower | engine |
| `search_max_matches` | int | 50 | 1 | 500 | lower | engine |
| `explanation_max_sentences` | int | 3 | 1 | 10 | lower | engine |
| `extra_refused_read_patterns` | list | (none) | - | - | add_only | engine |
| `token_ceiling` | int | 100000 | 1 | 5000000 | lower | engine |
| `shared_pr_max` | int | 10 | 1 | 50 | lower | engine |
| `branch_prefix` | str | gozu/fix- | - | - | locked | engine |
| `severity_map` | map | BLOCKER=high, CRITICAL=high, MAJOR=medium, MINOR=low, INFO=low, HIGH=high, MEDIUM=medium, LOW=low | - | - | raise_only | engine |
| `eligible_label` | str | veil-eligible | - | - | free | shell |
| `failed_fix_label` | str | veil-failed-fix | - | - | free | engine |
| `in_review_status` | str | In Review | - | - | locked | engine |
| `jira_site_url` | str | (empty) | - | - | locked | shell |
| `jira_project_keys` | list | (none) | - | - | locked | shell |
| `jira_email_env` | str | JIRA_EMAIL | - | - | free | shell |
| `jira_token_env` | str | JIRA_API_TOKEN | - | - | free | shell |
| `openai_key_env` | str | OPENAI_API_KEY | - | - | free | shell |
| `schedule_enabled` | bool | false | - | - | disable_only | shell |
| `on_demand_enabled` | bool | true | - | - | disable_only | shell |
| `event_enabled` | bool | true | - | - | disable_only | shell |

## What a repo may do with a value that the org set

- `lower`: A repo may lower the value. It may not raise it.
- `add_only`: A repo may add entries. It may not drop one.
- `raise_only`: A repo may raise a severity bucket. It may not lower one.
- `disable_only`: A repo may turn the setting off. It may not turn it on.
- `locked`: A repo may not change the value.
- `free`: A repo may set any value that the bounds allow.
