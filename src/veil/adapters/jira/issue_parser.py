from veil.adapters.jira.adf import details_of, finding_text
from veil.adapters.jira.constants.details import (
    COMPONENT_SEPARATOR,
    CUSTOM_FIELD_NAMES,
    DETAIL_BRANCH,
    DETAIL_COMPONENT,
    DETAIL_LINE,
    DETAIL_REPOSITORY,
    DETAIL_SEVERITY,
    UNKNOWN_BRANCH,
)
from veil.engine.models.ticket.ticket import Ticket


def ticket_from_issue(
    issue: dict, custom_ids: dict[str, str] | None = None
) -> Ticket | None:
    """Build a ticket from a Jira issue that Gozurion made. Return None if the issue is not a finding of one line.

    A roll-up ticket, a finding with no line and a ticket with an unknown branch give None.
    """
    key = issue["key"]
    fields = issue["fields"]
    description = fields.get("description")
    if not isinstance(description, dict):
        return None
    details = details_of(description)
    for name, field_name in CUSTOM_FIELD_NAMES.items():
        value = _custom_text(fields.get((custom_ids or {}).get(field_name, "")))
        if value:
            details.setdefault(name, value)
    component = details.get(DETAIL_COMPONENT, "")
    path = _path_of(component)
    line = details.get(DETAIL_LINE, "")
    branch = details.get(DETAIL_BRANCH, "")
    repo = details.get(DETAIL_REPOSITORY, "")
    severity = details.get(DETAIL_SEVERITY, "")
    finding = finding_text(description)
    if not (path and line.isdigit() and repo and severity and finding):
        return None
    if not branch or branch == UNKNOWN_BRANCH:
        return None
    return Ticket(
        key=key,
        repo=repo,
        file=path,
        line=int(line),
        severity=severity,
        finding=finding,
        branch=branch,
        labels=tuple(fields.get("labels", [])),
    )


def _custom_text(value: object) -> str:
    """The text of a custom field value. A number field can give 12.0. An option field gives an object."""
    if isinstance(value, dict):
        value = value.get("value") or value.get("name")
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return "" if value in (None, "") else str(value)


def _path_of(component: str) -> str:
    """A Sonar component is `project:path`. Cut the project. A path that has a colon keeps its folders."""
    prefix, separator, rest = component.partition(COMPONENT_SEPARATOR)
    if separator and "/" not in prefix and "\\" not in prefix:
        return rest
    return component
