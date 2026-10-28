import re

# The kind of secret and a pattern that finds it. The kind goes in the reason of a failed attempt.
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "a private key header",
        re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
    ),
    ("an AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("a GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("a Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("a Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("an API key that starts with sk-", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("an Atlassian API token", re.compile(r"\bATATT3[A-Za-z0-9_\-=]{20,}")),
)
