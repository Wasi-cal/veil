# Veil

An agent that takes the Jira tickets that Gozu creates from scan findings. It fixes the flagged code and opens pull requests for human review.

## Language

**Gozu Ticket**:
An open Jira ticket that Gozu creates from a scan finding. It carries the repository, file, line, severity and branch of that finding. The branch is the branch of the Source PR. The agent never picks up a Gozu Ticket about a `gozu/fix-*` branch. A human decides what happens to it.
_Avoid_: Issue, finding (a finding is the scanner's record, and the ticket is Jira's)

**Fix**:
The code change that addresses one Gozu Ticket. It has its own commit.
_Avoid_: Patch, remediation

**Fix PR**:
A draft pull request that the agent opens. It contains one or more Fixes. It targets the branch of the Source PR.
_Avoid_: Bot PR, auto-PR

**Source PR**:
The open pull request that a developer raised and that Gozu scanned. A Gozu Ticket belongs to it. The Engine fixes the code in its branch and bases the Fix PR on that branch.
_Avoid_: Parent PR, original PR

**Shared PR**:
The Fix PR that carries the Low and Medium Fixes for one repository.
_Avoid_: Batch PR, bulk PR

**High PR**:
A Fix PR that carries the Fix for a single High-severity Gozu Ticket.
_Avoid_: Critical PR, separate PR

**Severity Bucket**:
The group of a Gozu Ticket by severity. The bucket decides which kind of Fix PR the ticket goes into. Low and Medium go together. High goes on its own.
_Avoid_: Priority tier

**Failed Fix**:
A Gozu Ticket that the agent could not fix safely. The ticket stays open with a comment and a marker label. It stays open until a human asks for another attempt.
_Avoid_: Rejected ticket, skipped ticket

**Engine**:
The part of the agent that selects tickets, groups them, produces Fixes and opens Fix PRs. It does not depend on how a run starts.
_Avoid_: Core, library

**Shell**:
A way to run the Engine. It is either the org-wide service or the GitHub Action in a single repository.
_Avoid_: Mode, wrapper
