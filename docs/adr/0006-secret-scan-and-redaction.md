# Secret scan and redaction

No secret may reach a commit, a pull request, a Jira comment, a log or a run report (ticket GR-8). The Engine has two guards.

## What we decided

- **The Shell gives the credential values.** The Context has a list of secrets. The Shell fills it with the credential values of the run. The Engine reads no environment variable, so it cannot find them alone. A value is a `SecretStr`. It does not show in `repr`, in logs or in a dump.
- **A value has at least 8 characters.** A shorter value would change normal text when the Engine redacts. The Context refuses it. It also refuses a value that is only white space. The error message never repeats a value.
- **The scan fails the attempt.** The Engine checks the files that the Fix edits, the commit message and the explanation. It looks for the credential values of the run and for known secret patterns. A match raises `AttemptFailed`. So the strong model gets one more try, as with any failed attempt. The reason names the kind of secret and where it is. It never holds the value.
- **Only new secrets count.** A secret counts only if the new text holds it more often than the old text. A secret that was in the file before does not block a Fix, even if the Fix edits the same line.
- **The scan runs before the syntax check.** A parser error can quote text from the edit, for example the name of a key. The scan finds the secret first, so the error never reaches a comment or a prompt.
- **The redaction covers the rest.** The Engine replaces each credential value and each text that matches a secret pattern with `[redacted]`. It does this in every text that it sends. These texts are the PR title and body, the commit message and the Jira comments. They are also the reasons of Failed Fixes, the reason that goes to the strong model and the run report. The Engine exports `redact` for adapters and Shells.
- **Overlaps.** Two matches that overlap become one `[redacted]`. So no part of a secret stays in the text, even when two credential values share some characters.
- **The first prompt.** The Engine redacts the first prompt before it goes to the model. This covers the ticket text, the path and the code around the line. A line that holds a credential value shows as `[redacted]`.
- **The patterns.** Private key headers, AWS key ids, GitHub tokens, Google API keys, Slack tokens, keys that start with `sk-` and Atlassian API tokens. The list is in `constants/secrets.py`. The marker `[redacted]` and the name of the credential kind are there too. We left out rules for text such as `password = "..."`, because they fail honest Fixes.

## What we accept for now

- The model cannot see the exact text of a line that holds a credential value. An edit that needs that text fails, and the attempt can fail. This is the cost of keeping the value away from the model.
- The Engine does not change errors that leave `run()`. The repo provider redacts git errors before it raises them (ticket GR-8). This keeps the error type, so a Shell can decide on a retry.
- The scan finds the exact value and the known patterns. It does not find a secret in another form. Examples are a value in base64, a value in other case, and a value that the model writes in two parts such as `'abc' + 'def'`.
- The Engine does not redact the branch name, the labels, the status or the URL of the PR. These values come from the tracker and from the repo provider, not from the model. The text `[redacted]` is not valid in a branch name.
- The Engine has no logging yet. A future log must use `redact`.
