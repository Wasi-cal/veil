# Settings catalog

The declaration of the settings makes this file. Do not edit it.
Run `python docs/settings/build.py` to make it again.

Each setting has a default in code. Four layers can change it. A later layer wins:
defaults, org settings, repo settings, per-run overrides.
Settings hold no secrets. The safety rules are code and are not settings.
The last column names the setting that holds the cache lifetime.

| Key | Default | Minimum | Maximum | Repo rule | Read by | Cache lifetime |
| --- | --- | --- | --- | --- | --- | --- |
| `cheap_model` | gpt-6-luna | - | - | free | engine | `cache_settings_ttl_seconds` |
| `strong_model` | gpt-6.1-terra | - | - | free | engine | `cache_settings_ttl_seconds` |
| `max_attempts` | 2 | 1 | 2 | lower | engine | `cache_settings_ttl_seconds` |
| `step_cap` | 25 | 1 | 100 | lower | engine | `cache_settings_ttl_seconds` |
| `diff_limit` | 200 | 0 | 2000 | lower | engine | `cache_settings_ttl_seconds` |
| `tool_result_max_bytes` | 8192 | 256 | 65536 | lower | engine | `cache_settings_ttl_seconds` |
| `read_file_max_lines` | 300 | 1 | 2000 | lower | engine | `cache_settings_ttl_seconds` |
| `search_max_matches` | 50 | 1 | 500 | lower | engine | `cache_settings_ttl_seconds` |
| `explanation_max_sentences` | 3 | 1 | 10 | lower | engine | `cache_settings_ttl_seconds` |
| `extra_refused_read_patterns` | (none) | - | - | add_only | engine | `cache_settings_ttl_seconds` |
| `token_ceiling` | 100000 | 1 | 5000000 | lower | engine | `cache_settings_ttl_seconds` |
| `model_calls_per_minute` | 20 | 1 | 600 | lower | shell | `cache_settings_ttl_seconds` |
| `shared_pr_max` | 10 | 1 | 50 | lower | engine | `cache_settings_ttl_seconds` |
| `branch_prefix` | gozu/fix- | - | - | locked | engine | `cache_settings_ttl_seconds` |
| `severity_map` | BLOCKER=high, CRITICAL=high, MAJOR=medium, MINOR=low, INFO=low, HIGH=high, MEDIUM=medium, LOW=low | - | - | raise_only | engine | `cache_settings_ttl_seconds` |
| `eligible_label` | veil-eligible | - | - | free | shell | `cache_settings_ttl_seconds` |
| `failed_fix_label` | veil-failed-fix | - | - | free | engine | `cache_settings_ttl_seconds` |
| `in_review_status` | In Review | - | - | locked | engine | `cache_settings_ttl_seconds` |
| `jira_site_url` | (empty) | - | - | locked | shell | `cache_settings_ttl_seconds` |
| `jira_project_keys` | (none) | - | - | locked | shell | `cache_settings_ttl_seconds` |
| `repos_allow` | (none) | - | - | locked | shell | `cache_settings_ttl_seconds` |
| `repos_deny` | (none) | - | - | locked | shell | `cache_settings_ttl_seconds` |
| `schedule_enabled` | false | - | - | disable_only | shell | `cache_settings_ttl_seconds` |
| `schedule_cron` | 0 6 * * * | - | - | locked | shell | `cache_settings_ttl_seconds` |
| `on_demand_enabled` | true | - | - | disable_only | shell | `cache_settings_ttl_seconds` |
| `event_enabled` | true | - | - | disable_only | shell | `cache_settings_ttl_seconds` |
| `quiet_window_minutes` | 10 | 0 | 120 | locked | shell | `cache_settings_ttl_seconds` |
| `run_timeout_minutes` | 60 | 1 | 240 | lower | shell | `cache_settings_ttl_seconds` |
| `heartbeat_seconds` | 120 | 10 | 600 | locked | shell | `cache_settings_ttl_seconds` |
| `max_concurrent_runs` | 3 | 1 | 20 | lower | shell | `cache_settings_ttl_seconds` |
| `checkout_sweep_minutes` | 60 | 10 | 1440 | locked | shell | `cache_settings_ttl_seconds` |
| `cache_settings_ttl_seconds` | 60 | 1 | 86400 | locked | shell | `cache_settings_ttl_seconds` |
| `cache_jira_metadata_ttl_seconds` | 300 | 1 | 86400 | locked | shell | `cache_settings_ttl_seconds` |
| `cache_repo_list_ttl_seconds` | 600 | 1 | 86400 | locked | shell | `cache_settings_ttl_seconds` |

## What a repo may do with a value that the org set

- `lower`: A repo may lower the value. It may not raise it.
- `add_only`: A repo may add entries. It may not drop one.
- `raise_only`: A repo may raise a severity bucket. It may not lower one.
- `disable_only`: A repo may turn the setting off. It may not turn it on.
- `locked`: A repo may not change the value.
- `free`: A repo may set any value that the bounds allow.
