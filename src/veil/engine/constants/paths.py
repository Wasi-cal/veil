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

# The model must never read these secret files. Settings can add patterns. Settings cannot remove these patterns.
READ_REFUSED_PATTERNS = (".env*", "*.pem", "*.key", "*.p12", "id_rsa*", ".npmrc")
READ_REFUSED_DIRS = (".git",)
