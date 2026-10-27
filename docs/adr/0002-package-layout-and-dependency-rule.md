# Package layout and dependency rule

The code has three layers: `engine`, `adapters` and `shells`. The `engine` package is the Engine. It holds the fix loop, grouping, eligibility rules, the run report, the settings schema and the interfaces (tracker, repo provider, model client). `engine` imports nothing from `adapters` or `shells`, and knows no Jira, GitHub, OpenAI, Temporal, PostgreSQL or Redis. `adapters` hold the real parts behind those interfaces (Jira, GitHub and git, OpenAI, the settings store, the cache). `shells` build the context and start runs (the GitHub Action, the Temporal service). Tests mirror this layout, with fakes for the interfaces kept beside `engine`.

We chose this so that one Engine serves both Shells (ADR 0001) and so that the Engine tests need no network, database or Temporal. A lint check on imports enforces the rule. A new tracker or model provider is a new adapter, with no change to `engine`.

Python package and folder names are chosen when GR-12 starts and follow this shape.
