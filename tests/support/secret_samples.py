"""Text that looks like a secret of each kind. Each sample is built from pieces."""

KEY_LIKE = {
    "rsa-private-key-header": "-----BEGIN " + "RSA PRIVATE KEY-----",
    "openssh-private-key-header": "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
    "aws-access-key-id": "AK" + "IA" + "IOSFODNN7EXAMPLE",
    "github-token": "gh" + "p_" + "A1" * 18,
    "google-api-key": "AI" + "za" + "SyA-" + "x" * 31,
    "slack-token": "xo" + "xb-" + "123456789012-abcdefghijkl",
    "sk-key": "s" + "k-" + "proj" + "a1" * 12,
    "atlassian-token": "AT" + "ATT3" + "xFfGF0" + "b" * 24,
}
