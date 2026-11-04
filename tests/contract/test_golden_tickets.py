import json
from pathlib import Path

import pytest

from tests.fakes.jira_fixtures import issue_json
from veil.adapters.jira.adf import details_of
from veil.adapters.jira.issue_parser import ticket_from_issue

GOLDEN = json.loads((Path(__file__).parent / "golden_tickets.json").read_text())


@pytest.mark.parametrize("case", GOLDEN["cases"], ids=lambda case: case["name"])
def test_veil_reads_the_golden_tickets_of_the_gozu_ticket_contract(case):
    expected = case["expected"]
    finding = case["finding"]
    issue = issue_json(
        "VT-1", details=expected["details"], labels=tuple(expected["labels"])
    )

    ticket = ticket_from_issue(issue, {})

    if finding["line"] is None and "package" not in finding:
        assert ticket is None  # No line and no Package line: not a finding veil can fix.
        return
    if finding["line"] is None:
        assert ticket is not None
        assert (ticket.package, ticket.installed_version, ticket.fixed_version) == (
            finding["package"],
            finding["installed_version"],
            finding["fixed_version"],
        )
        assert ticket.line is None
    assert ticket is not None
    assert (ticket.repo, ticket.file, ticket.line) == (
        finding["repo"],
        finding["component"],
        finding["line"],
    )
    assert ticket.severity == finding["severity"]
    assert ticket.branch == finding["branch"]
    assert ticket.issue_label == expected["labels"][0]


PACKAGE_CASES = [case for case in GOLDEN["cases"] if "package" in case["finding"]]


def test_the_golden_tickets_have_a_package_case_with_no_line():
    assert [case["finding"]["line"] for case in PACKAGE_CASES] == [None]


@pytest.mark.parametrize("case", PACKAGE_CASES, ids=lambda case: case["name"])
def test_the_package_lines_of_a_golden_ticket_reach_the_details_veil_reads(case):
    finding = case["finding"]
    expected = case["expected"]
    issue = issue_json(
        "VT-1", details=expected["details"], labels=tuple(expected["labels"])
    )

    details = details_of(issue["fields"]["description"])

    assert details["Package"] == finding["package"]
    assert details["Installed version"] == finding["installed_version"]
    assert details["Fixed version"] == finding["fixed_version"]
    assert "Line" not in details
    assert expected["details"][1:4] == [
        f"Component: {finding['component']}",
        f"Package: {finding['package']}",
        f"Installed version: {finding['installed_version']}",
    ]
