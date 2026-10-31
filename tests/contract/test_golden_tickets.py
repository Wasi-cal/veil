import json
from pathlib import Path

import pytest

from tests.fakes.jira_fixtures import issue_json
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

    if finding["line"] is None:
        assert ticket is None  # A finding with no line is not a one-line finding.
        return
    assert ticket is not None
    assert (ticket.repo, ticket.file, ticket.line) == (
        finding["repo"],
        finding["component"],
        finding["line"],
    )
    assert ticket.severity == finding["severity"]
    assert ticket.branch == finding["branch"]
    assert ticket.issue_label == expected["labels"][0]
