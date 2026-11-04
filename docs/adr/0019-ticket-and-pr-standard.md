# One standard for tickets, commits and PRs

Gozurion and the Gozu CLI write the tickets. veil reads them and opens the PRs. Before this ADR the two writers made different tickets, and veil could not read the Gozu CLI tickets at all.

## What we decided

- **One contract.** `docs/ticket-contract.md` says how a ticket looks: the title, the labels and the Details list. The same page is in Gozurion and in the Gozu CLI. Golden tickets in `tests/contract/golden_tickets.json` are in all three repos. Each repo has a test against them. `gozu/scripts/check-ticket-contract.sh` fails if the copies differ.
- **The title carries the repository and the file.** The form is `repo | file | line | title`, with at most 120 characters. A board shows what and where without a click. The Details list keeps the owner and the full path.
- **The labels are a fixed set.** They are `issue-<id>`, `<tool>` and `branch-<branch>`. The identity in `issue-<id>` is the same formula in both writers. So one finding gives one ticket, also when both tools scan one repo.
- **A ticket always has a repository and a branch.** A tool that finds none stops before it writes. veil skips a ticket that has none.
- **Commits are Conventional Commits.** The subject is `fix(security): <summary>`, at most 72 characters, with no full stop. The footer is `Refs: <ticket>`. The Engine sends a different subject back to the model.
- **PR titles start with the tickets.** One ticket: `VT-10 | <commit subject>`. Many tickets: `VT-10 | VT-11 | fix(security): resolve N findings in <file>`.
- **PR bodies have a fixed shape.** A summary, then one section for each ticket with the three parts: why it is a problem, what changed and what it solves. The model writes them in its own words. The Engine refuses a copy of the ticket.

## What we accept for now

- The golden file and the contract page exist in three copies. A script checks them, but a person must run it.
- The Gozu CLI webhook path needs `repo_full_name` in the config. A config without it gets no tickets until it has one.
- Tickets that the old writers made, such as VT-1 to VT-9, have no repository and no `issue-` label. veil cannot read them. Close or delete them.
- A rule title in the ticket comes from the scanner. veil does not rewrite it.
