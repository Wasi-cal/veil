# One engine, two shells

The agent runs both as an org-wide service and as a GitHub Action in a single repo (Dependabot-style). We build one Engine and two thin Shells rather than two products, so grouping, fixing and Jira-sync behavior cannot drift between them. Each Shell supplies its own repo access: the service uses a GitHub App across the org, the Action uses the workflow's own token and handles only its own repo.
