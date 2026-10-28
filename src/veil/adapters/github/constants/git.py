GITHUB_URL = "https://github.com/"
# GitHub accepts any user name with a token in basic authentication. This is the name that its docs use.
TOKEN_USER = "x-access-token"
REF_PREFIX = "refs/heads/"
AUTHOR_NAME = "Gozu Veil"
AUTHOR_EMAIL = "veil@gozu.invalid"
# Git needs these to reach GitHub through a proxy or with a company certificate.
NETWORK_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "GIT_SSL_CAINFO",
)
