"""GitHub pull request answers. The fields are the ones that the adapter reads."""


def pull_json(
    number: int = 1,
    head: str = "feature-x",
    base: str = "main",
    state: str = "open",
    merged: bool = False,
    head_repo: str = "acme/app",
    labels: tuple[str, ...] = (),
    draft: bool = False,
) -> dict:
    """The fields of a GitHub pull request that the adapter reads."""
    return {
        "number": number,
        "html_url": f"https://github.example.invalid/acme/app/pull/{number}",
        "state": state,
        "merged_at": "2026-01-01T00:00:00Z" if merged else None,
        "draft": draft,
        "title": "t",
        "body": "b",
        "head": {"ref": head, "repo": {"full_name": head_repo}},
        "base": {"ref": base, "repo": {"full_name": "acme/app"}},
        "labels": [{"name": name} for name in labels],
    }
