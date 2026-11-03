# The token cap is for one ticket

The owner of the project decided this on 2026-11-03. It replaces the token ceiling of the run.

## What we decided

- **One cap for each ticket.** The setting `ticket_token_cap` is the most tokens that one ticket may use, over all its attempts. The default is 100,000.
- **No cap for the run.** The setting `token_ceiling` is gone. A repo file that sets it fails with "unknown setting".
- **At the cap the ticket is a Failed Fix.** The Engine checks the count before each model call. At the cap, the Engine drops the edits of the ticket. The ticket gets the label `veil-failed-fix` and a comment. It stays open. A person decides what happens next.
- **The run goes on.** The next ticket has a new count. The Fixes that passed are published as before.
- **A finished fix stays.** If the last call of a fix passes the cap, the Engine still keeps the fix. The next call does not start.
- **The report.** The run report still shows the tokens that all tickets used.

## What this costs

- **No limit on the cost of a run.** Cost is up to the cap times the number of tickets. One hundred tickets can use ten million tokens at the default cap. A person who wants a cheaper run must lower the cap or give fewer tickets (label, assignee or project).
- **A ticket that is too big always fails.** The label stops the next run from trying it again. A person must remove the label to ask for another attempt.
- **A run that the cap used to stop now ends with many Failed Fixes.** The old outcome `left_for_next_run` still exists. It now means that GitHub refused the token (`token_expired`).
