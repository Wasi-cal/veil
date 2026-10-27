# One engine, two shells

The agent runs as an org-wide service and as a GitHub Action in a single repo (Dependabot-style). We build one Engine and two thin Shells. We do not build two products. Then grouping, fixing and Jira-sync behavior cannot drift between the Shells.

Each Shell supplies its own repo access. The service uses a GitHub App across the org. The Action uses the token of its workflow and handles only its own repo.
