# Veil for Gozu Tickets

Veil reads the open Gozu Tickets of your repo in Jira. It changes the code in a private copy. Then it opens a Fix PR for a person to review.

**Veil never merges.** A person reviews every Fix PR and decides.

## What you need

- A repo on GitHub.
- A Jira Cloud site with Gozu Tickets. Gozu writes one ticket for each scan finding. The ticket must follow [the ticket contract](docs/ticket-contract.md).
- An OpenAI API key.
- Three repo secrets: `JIRA_EMAIL`, `JIRA_API_TOKEN` and `OPENAI_API_KEY`.
- One repo setting. Go to Settings, Actions, General, Workflow permissions. Turn on "Allow GitHub Actions to create and approve pull requests". Without it, GitHub refuses to open the PR.

`GITHUB_TOKEN` comes from the workflow. You do not create it.

## Quick start

1. Add the settings file `.gozu/jira-to-pr.yml` to your repo:

   ```yaml
   jira_site_url: "https://yourco.atlassian.net"
   jira_project_keys: ["SEC"]
   ```

2. Add the workflow `.github/workflows/veil.yml`:

   ```yaml
   name: veil
   on:
     workflow_dispatch:
   permissions:
     contents: write
     pull-requests: write
   concurrency:
     group: veil-${{ github.repository }}
     cancel-in-progress: false
   jobs:
     veil:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
           with:
             persist-credentials: false
         - uses: Wasi-cal/veil@v1
           env:
             GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
             JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
             JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
             OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
   ```

3. Start the workflow by hand. Read the run summary. Then review the Fix PRs.

The Action needs `actions/checkout` first, because it reads `.gozu/jira-to-pr.yml` from the checkout.

## What a run does

1. It reads your settings and checks the event. It stops with one error line if a check fails. It changes no ticket in that case.
2. It finds the open tickets of this repo. It skips a ticket that has a Fix PR (open or merged), a failed Fix, or a closed Source PR.
3. It makes one group for each file. Tickets for the same file share a group. Each group gets one Fix PR. High severity goes first.
4. For each ticket, an AI model reads the code and edits it in a private clone. It has five tools: read, search, list, edit and finish. It has no shell and no network.
5. The Engine checks every edit and every Fix. Then it commits the Fix and opens the PR, ready for review.
6. Veil comments on each ticket and sets its status to In Review. It never moves a ticket to Done.
7. Veil writes a report to the run summary.

## When a run starts

| Event | Default | Setting |
|---|---|---|
| `workflow_dispatch` | on | `on_demand_enabled` |
| `repository_dispatch` | on | `event_enabled` |
| `schedule` | off | `schedule_enabled` |
| `pull_request` | off | `pull_request_enabled` |

A `pull_request` run sees only the tickets of the branch of that PR. A PR from a fork never runs. No other event can start a run. Never use `pull_request_target`.

## Safety rules

These rules are code. A setting cannot turn them off.

- Veil never merges and never opens a PR from or against the default branch.
- Veil never runs on its own Fix branches, and never fixes a ticket again after its Fix PR is merged.
- Veil never pushes to your branch. It pushes its own `gozu/fix-*` branches.
- Veil never reads, lists or edits anything in `.github/`, lockfiles or secret files such as `.env` and keys.
- Veil never follows a symlink, so a link cannot hide a protected file.
- Veil never creates or deletes a file.
- Veil treats ticket text and repo files as data. It never follows instructions in them.
- A secret never goes into a commit, a PR, a comment, a log or the report. Veil hides known secret patterns and the credentials of the run.

## Cost and data

- Each ticket has a token cap, `ticket_token_cap`. The default is 100,000 tokens. A ticket that uses its cap becomes a Failed Fix. **There is no cap for the whole run.** The cost can reach the cap times the number of tickets.
- Veil sends the text of the ticket and the code that the model reads to the OpenAI API. It asks OpenAI not to store the conversation.
- Add a branch rule that needs a review before a merge. A Fix PR opens ready for review, not as a draft.

## More

- [All settings](docs/settings.md)
- [How veil works](docs/how-it-works.md)
- [Decisions](docs/adr)

## License

Copyright (c) 2026 Calfus. All rights reserved. See [LICENSE](LICENSE). You may run the Action in your own workflows.
