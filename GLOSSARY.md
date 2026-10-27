# Jira to PR

An agent that takes the Jira tickets Gozu creates from scan findings, fixes the flagged code, and opens pull requests for human review.

## Language

**Gozu Ticket**:
An open Jira ticket created by Gozu from a scan finding, carrying the repository, file, line and severity of that finding. A Gozu Ticket raised against a `gozu/fix-*` branch is never picked up automatically; a human decides what happens to it.
_Avoid_: Issue, finding (a finding is the scanner's record; the ticket is Jira's)

**Fix**:
The code change that addresses one Gozu Ticket, kept as its own commit.
_Avoid_: Patch, remediation

**Fix PR**:
A draft pull request the agent opens containing one or more Fixes.
_Avoid_: Bot PR, auto-PR

**Shared PR**:
The Fix PR that carries the Low and Medium Fixes for one repository.
_Avoid_: Batch PR, bulk PR

**High PR**:
A Fix PR that carries the Fix for a single High-severity Gozu Ticket.
_Avoid_: Critical PR, separate PR

**Severity Bucket**:
The grouping of a Gozu Ticket by severity that decides which kind of Fix PR it goes into: Low and Medium together, High on its own.
_Avoid_: Priority tier

**Failed Fix**:
A Gozu Ticket the agent could not fix safely; it stays open with a comment and a marker label until a human asks for another attempt.
_Avoid_: Rejected ticket, skipped ticket

**Engine**:
The part of the agent that selects tickets, groups them, produces Fixes and opens Fix PRs, independent of how a run is started.
_Avoid_: Core, library

**Shell**:
A way of running the Engine: either the org-wide service or the GitHub Action inside a single repository.
_Avoid_: Mode, wrapper
