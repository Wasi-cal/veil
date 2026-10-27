PROTECTED_DIRS = (".github/workflows",)

LOCKFILE_NAMES = frozenset(
    {
        "uv.lock",
        "poetry.lock",
        "pipfile.lock",
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lockb",
        "cargo.lock",
        "gemfile.lock",
        "composer.lock",
        "go.sum",
    }
)

# Secret files the model may never read. Settings can add patterns, never remove these.
READ_REFUSED_PATTERNS = (".env*", "*.pem", "*.key", "*.p12", "id_rsa*", ".npmrc")
READ_REFUSED_DIRS = (".git",)
