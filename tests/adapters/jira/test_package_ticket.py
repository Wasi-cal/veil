from tests.fakes.jira_fixtures import issue_json
from veil.adapters.jira.issue_parser import ticket_from_issue

BASE = [
    "Repository: acme/app",
    "Component: requirements.txt",
    "Type: vulnerability",
    "Rule: CVE-2018-1000656",
    "Severity: HIGH",
    "Source: trivy",
    "Branch: main",
    "Commit: def4567890",
]
PACKAGE = ["Package: flask", "Installed version: 0.12.2", "Fixed version: 0.12.3, 1.0"]


def ticket_for(*details):
    return ticket_from_issue(issue_json("VT-1", details=list(details)), {})


def test_a_ticket_with_a_package_line_and_no_line_is_a_package_ticket():
    ticket = ticket_for(*BASE[:2], *PACKAGE, *BASE[2:])

    assert ticket is not None
    assert ticket.line is None
    assert (ticket.file, ticket.package) == ("requirements.txt", "flask")
    assert ticket.installed_version == "0.12.2"
    assert ticket.fixed_version == "0.12.3, 1.0"


def test_a_package_ticket_with_no_fixed_version_has_none():
    ticket = ticket_for(*BASE[:2], *PACKAGE[:2], *BASE[2:])

    assert ticket is not None
    assert ticket.fixed_version is None


def test_a_ticket_with_no_line_and_no_package_line_is_skipped():
    assert ticket_for(*BASE) is None


def test_a_ticket_with_a_line_keeps_it_and_has_no_package():
    ticket = ticket_for(*BASE[:2], "Line: 5", *BASE[2:])

    assert ticket is not None
    assert (ticket.line, ticket.package) == (5, None)
