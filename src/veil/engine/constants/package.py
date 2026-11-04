# The manifest that goes with each lockfile. A package Fix edits the manifest and never the lockfile.
LOCKFILE_MANIFESTS = {
    "uv.lock": "pyproject.toml",
    "poetry.lock": "pyproject.toml",
    "pipfile.lock": "Pipfile",
    "package-lock.json": "package.json",
    "npm-shrinkwrap.json": "package.json",
    "yarn.lock": "package.json",
    "pnpm-lock.yaml": "package.json",
    "bun.lockb": "package.json",
    "cargo.lock": "Cargo.toml",
    "gemfile.lock": "Gemfile",
    "composer.lock": "composer.json",
    "go.sum": "go.mod",
}

# The most lines of the manifest that the first prompt shows. The model can read the rest with read_file.
MANIFEST_PROMPT_LINES = 200
