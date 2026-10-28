"""Jira Cloud REST v3 response shapes. The ticket text follows what Gozurion writes in `ticket/jira_client.py`.

These are written by hand from the Jira Cloud REST documentation. They are not recorded from a live site.
"""


def _paragraph(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def adf_description(summary: str, details: list[str], full: str | None = None) -> dict:
    """The description that Gozurion builds: a short paragraph, an optional full text and a Details list."""
    content = [_paragraph(summary)]
    if full:
        content.append(
            {
                "type": "expand",
                "attrs": {"title": "Full description"},
                "content": [_paragraph(full)],
            }
        )
    content.append(
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Details"}],
        }
    )
    content.append(
        {
            "type": "bulletList",
            "content": [
                {"type": "listItem", "content": [_paragraph(line)]} for line in details
            ],
        }
    )
    return {"type": "doc", "version": 1, "content": content}


def gozurion_details(
    repo: str = "acme/app",
    component: str = "acme_app:src/app.py",
    line: int | None = 3,
    severity: str = "HIGH",
    branch: str = "feature/login",
) -> list[str]:
    details = [f"Repository: {repo}", f"Component: {component}"]
    if line is not None:
        details.append(f"Line: {line}")
    details += [
        "Type: vulnerability",
        "Rule: python:S5334",
        f"Severity: {severity}",
        "Source: sonarqube",
        f"Branch: {branch}",
        "Commit: 0123456789",
    ]
    return details


def issue_json(
    key: str = "SEC-7",
    labels: tuple[str, ...] = ("issue-3f9a", "branch-feature/login", "veil-eligible"),
    details: list[str] | None = None,
    summary: str = "Avoid eval on user input.",
    full: str | None = "Avoid eval on user input. It runs code that comes from a user.",
    extra_fields: dict | None = None,
) -> dict:
    return {
        "id": "10001",
        "key": key,
        "fields": {
            "labels": list(labels),
            "description": adf_description(
                summary, gozurion_details() if details is None else details, full
            ),
            **(extra_fields or {}),
        },
    }


def search_page(issues: list[dict], next_page_token: str | None = None) -> dict:
    page: dict = {"issues": issues}
    if next_page_token:
        page["nextPageToken"] = next_page_token
    return page
