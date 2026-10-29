import hashlib
from collections.abc import Generator
from contextlib import contextmanager

from veil.adapters.jira.adf import comment_body
from veil.adapters.jira.constants.details import (
    CUSTOM_FIELD_NAMES,
)
from veil.adapters.jira.constants.http import (
    COMMENT_SEGMENT,
    FIELD_PATH,
    ISSUE_PATH,
    PAGE_SIZE,
    SEARCH_PATH,
    TRANSITIONS_SEGMENT,
)
from veil.adapters.jira.constants.patterns import ISSUE_KEY, SAFE_LABEL
from veil.adapters.jira.constants.workflow import COMMENT_PROPERTY_KEY, DONE_CATEGORY
from veil.adapters.jira.http_client import JiraHttp
from veil.adapters.jira.issue_parser import ticket_from_issue
from veil.adapters.jira.models.jira_credentials import JiraCredentials
from veil.adapters.jira.models.jira_settings import JiraSettings
from veil.engine.errors.tracker_error import TrackerError
from veil.engine.models.ticket.ticket import Ticket


@contextmanager
def _expected_shape(what: str) -> Generator[None]:
    """Turn a missing key or a wrong kind of value in a Jira answer into a TrackerError."""
    try:
        yield
    except (KeyError, TypeError, AttributeError, ValueError):
        raise TrackerError(f"Jira gave {what} in an unexpected shape.") from None


class JiraTracker:
    """The real tracker. It satisfies the Tracker interface of the Engine.

    Jira statuses, JQL and label names live here and nowhere else.
    """

    def __init__(
        self,
        settings: JiraSettings,
        credentials: JiraCredentials,
        api_base: str | None = None,
    ):
        self._settings = settings
        self._http = JiraHttp(api_base or settings.site_url, credentials)

    def open_tickets(self) -> list[Ticket]:
        tickets: list[Ticket] = []
        page_token: str | None = None
        custom_ids = self._custom_field_ids()
        while True:
            body: dict = {
                "jql": self._jql(),
                "fields": ["labels", "description", *custom_ids.values()],
                "maxResults": PAGE_SIZE,
            }
            if page_token:
                body["nextPageToken"] = page_token
            page = self._http.call("POST", SEARCH_PATH, body=body, shape=dict)
            with _expected_shape("the search answer"):
                for issue in page["issues"]:
                    ticket = ticket_from_issue(issue, custom_ids)
                    if ticket is not None:
                        tickets.append(ticket)
                page_token = page.get("nextPageToken")
            if not page_token:
                return tickets

    def add_comment(self, key: str, text: str) -> None:
        """Post the comment with a hidden marker. Skip it if a comment of the ticket has that marker."""
        self._check_key(key)
        marker = hashlib.sha256(text.encode()).hexdigest()[:32]
        if self._has_marker(key, marker):
            return
        self._http.call(
            "POST",
            f"{ISSUE_PATH}/{key}/{COMMENT_SEGMENT}",
            body={
                "body": comment_body(text),
                "properties": [
                    {"key": COMMENT_PROPERTY_KEY, "value": {"marker": marker}}
                ],
            },
        )

    def _has_marker(self, key: str, marker: str) -> bool:
        start = 0
        while True:
            page = self._http.call(
                "GET",
                f"{ISSUE_PATH}/{key}/{COMMENT_SEGMENT}",
                params={
                    "expand": "properties",
                    "startAt": start,
                    "maxResults": PAGE_SIZE,
                },
                shape=dict,
            )
            with _expected_shape("the comments"):
                for comment in page["comments"]:
                    for prop in comment.get("properties", []):
                        if prop.get("key") == COMMENT_PROPERTY_KEY and (
                            prop.get("value", {}).get("marker") == marker
                        ):
                            return True
                start += len(page["comments"])
                if not page["comments"] or start >= page["total"]:
                    return False

    def add_label(self, key: str, label: str) -> None:
        """Ask Jira to add the label. Jira keeps one copy, so a repeat gives the same state."""
        self._check_key(key)
        if not SAFE_LABEL.fullmatch(label):
            raise TrackerError("Refused the label. Jira labels have no space or quote.")
        self._http.call(
            "PUT",
            f"{ISSUE_PATH}/{key}",
            body={"update": {"labels": [{"add": label}]}},
        )

    def set_status(self, key: str, status: str) -> None:
        """Move the ticket to the status. Do nothing if it is there. Never move it to a done status."""
        self._check_key(key)
        target = self._settings.status_names.get(status, status)
        issue = self._http.call(
            "GET", f"{ISSUE_PATH}/{key}", params={"fields": "status"}
        )
        with _expected_shape("the status of the ticket"):
            current = issue["fields"]["status"]["name"]
        if current.casefold() == target.casefold():
            return
        reply = self._http.call(
            "GET", f"{ISSUE_PATH}/{key}/{TRANSITIONS_SEGMENT}", shape=dict
        )
        with _expected_shape("the transitions"):
            chosen = next(
                (
                    t
                    for t in reply["transitions"]
                    if t["to"]["name"].casefold() == target.casefold()
                ),
                None,
            )
        if chosen is None:
            raise TrackerError(f"The workflow of {key} has no transition to {target}.")
        with _expected_shape("the transitions"):
            category = chosen["to"]["statusCategory"]["key"]
        if category == DONE_CATEGORY:
            raise TrackerError(
                f"Refused to move {key} to {target}. The status is in the {DONE_CATEGORY} "
                "category, and the adapter never closes a ticket."
            )
        self._http.call(
            "POST",
            f"{ISSUE_PATH}/{key}/{TRANSITIONS_SEGMENT}",
            body={"transition": {"id": chosen["id"]}},
        )

    @staticmethod
    def _check_key(key: str) -> None:
        if not ISSUE_KEY.fullmatch(key):
            raise TrackerError("Refused the ticket key.")

    def _custom_field_ids(self) -> dict[str, str]:
        """The ids of the custom fields that Gozurion fills, by field name. A site can have none."""
        wanted = set(CUSTOM_FIELD_NAMES.values())
        fields = self._http.call("GET", FIELD_PATH, shape=list)
        with _expected_shape("the list of fields"):
            return {f["name"]: f["id"] for f in fields if f.get("name") in wanted}

    def _jql(self) -> str:
        projects = ", ".join(f'"{key}"' for key in self._settings.project_keys)
        return (
            f"project in ({projects}) "
            f'AND labels = "{self._settings.eligible_label}" '
            "AND statusCategory != Done AND assignee is EMPTY ORDER BY key ASC"
        )
