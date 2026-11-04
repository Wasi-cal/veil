# Veil

An agent that takes the Jira tickets that Gozu creates from scan findings. It fixes the flagged code and opens pull requests for human review.

## Language

**Gozu Ticket**:
An open Jira ticket that Gozu creates from a scan finding. It carries the repository, file, line, severity and branch of that finding. The branch is the branch of the Source PR. The agent never picks up a Gozu Ticket about a Fix branch. A human decides what happens to it.
_Avoid_: Issue, finding (a finding is the scanner's record, and the ticket is Jira's)

**Fix**:
The code change that addresses one Gozu Ticket. It has its own commit.
_Avoid_: Patch, remediation

**Fix PR**:
A pull request that the agent opens, ready for review. It contains one or more Fixes. It targets the branch of the Source PR.
_Avoid_: Bot PR, auto-PR

**Source PR**:
The open pull request that a developer raised and that Gozu scanned. A Gozu Ticket belongs to it. The Engine fixes the code in its branch and bases the Fix PR on that branch.
_Avoid_: Parent PR, original PR

**Fix group**:
The Gozu Tickets that go into one Fix PR. One ticket gives one group. Tickets that flag the same file in the same Source PR share a group, because their Fixes overlap. There is no cap on the number of groups.
_Avoid_: Shared PR, High PR, batch

**Severity Bucket**:
The group of a Gozu Ticket by severity: High, Medium or Low. The bucket sets the order of the Fix groups, High first. It does not decide which tickets share a PR. A setting, the severity map, gives the bucket of each severity word.
_Avoid_: Priority tier

**Credential**:
A value that gives access to a service, for example a token or an API key. The Shell gives the credential values of a run to the Engine.
_Avoid_: Password, key (a key can also be a ticket key)

**Secret**:
A credential value of the run, or a text that matches a known secret pattern, for example a private key header. A Fix must never hold a secret, and the Engine never sends one.
_Avoid_: Sensitive data

**Ticket token cap**:
The most tokens that one ticket may use, over all its attempts. The code also calls it the budget. A ticket that uses its cap becomes a Failed Fix. The run goes on with the next ticket. There is no cap for the whole run.
_Avoid_: Quota, limit (the diff limit is another rule), token ceiling (the old name)

**Failed Fix**:
A Gozu Ticket that the agent could not fix safely. The ticket stays open with a comment and a marker label. It stays open until a human asks for another attempt.
_Avoid_: Rejected ticket, skipped ticket

**Breaking change**:
A Fix that may break something outside the lines it edits: code, config, a build, a test or a user. An incompatible change to a public interface counts, and so does a Fix that rejects input that used to work. Veil marks the ticket and says why. A person decides what to do.
_Avoid_: Regression (a bug that already happened; a breaking change is a risk before the merge), Incompatibility

**Engine**:
The part of the agent that selects tickets, groups them, produces Fixes and opens Fix PRs. It does not depend on how a run starts.
_Avoid_: Core, library

**Shell**:
A way to run the Engine. It is either the org-wide service or the GitHub Action in a single repository.
_Avoid_: Mode, wrapper

**Settings snapshot**:
The settings rows of the org and of the repos of one run, read from the database at one point in time. The service reads it once at the start of a run, and the whole run uses it. A change in the database applies to the next run.
_Avoid_: Config cache, settings copy

**Stopped run**:
A run that ended before it handled every ticket, because GitHub refused the token. The token of a job expires after one hour. The report says `token_expired`. Each ticket without an outcome stays open for the next run.
_Avoid_: Failed run (a Failed Fix is another thing)

