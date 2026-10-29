import hashlib
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

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
from veil.adapters.jira.constants.workflow import (
    COMMENT_PROPERTY_KEY,
    DONE_CATEGORY,
    STALE_TRANSITION_STATUSES,
)
from veil.adapters.jira.http_client import JiraHttp
from veil.adapters.jira.issue_parser import ticket_from_issue
from veil.adapters.jira.metadata_cache import MetadataCache, NoMetadataCache
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


def _issue_type_of(issue: dict[str, Any]) -> str | None:
    """The id of the issue type. A ticket with no issue type in the answer gets no cache."""
    try:
        issue_type = issue["fields"]["issuetype"]["id"]
    except (KeyError, TypeError):
        return None
    return issue_type if isinstance(issue_type, str) and issue_type else None


def _pick(status: str, transitions: list[dict[str, Any]]) -> dict[str, Any] | None:
    with _expected_shape("the transitions"):
        return next(
            (t for t in transitions if t["to"]["name"].casefold() == status.casefold()),
            None,
        )


def _refuse_done(key: str, status: str, chosen: dict[str, Any]) -> None:
    with _expected_shape("the transitions"):
        category = chosen["to"]["statusCategory"]["key"]
    if category == DONE_CATEGORY:
        raise TrackerError(
            f"Refused to move {key} to {status}. The status is in the {DONE_CATEGORY} "
            "category, and the adapter never closes a ticket."
        )


class JiraTracker:
    """The real tracker. It satisfies the Tracker interface of the Engine.

    Jira statuses, JQL and label names live here and nowhere else.
    """

    def __init__(
        self,
        settings: JiraSettings,
        credentials: JiraCredentials,
        api_base: str | None = None,
        metadata_cache: MetadataCache | None = None,
    ):
        self._settings = settings
        self._metadata = metadata_cache or NoMetadataCache()
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
        issue = self._http.call(
            "GET",
            f"{ISSUE_PATH}/{key}",
            params={"fields": "status,issuetype"},
        )
        with _expected_shape("the status of the ticket"):
            current = issue["fields"]["status"]["name"]
        if current.casefold() == status.casefold():
            return
        scope = (key.rsplit("-", 1)[0], _issue_type_of(issue), current)
        if not self._move_from_cache(key, status, scope):
            self._move_from_jira(key, status, scope)

    def _move_from_cache(
        self, key: str, status: str, scope: tuple[str, str | None, str]
    ) -> bool:
        """Move the ticket with a cached transition. Give False if the cache cannot do it."""
        project, issue_type, current = scope
        if issue_type is None:
            return False
        cached = self._metadata.transitions(project, issue_type, current)
        chosen = _pick(status, cached) if cached is not None else None
        if chosen is None:
            return False
        _refuse_done(key, status, chosen)
        try:
            self._post_transition(key, chosen)
        except TrackerError as failure:
            if failure.status not in STALE_TRANSITION_STATUSES:
                raise
            # Jira says that the move is not valid. The workflow can have changed.
            self._metadata.forget_transitions(project, issue_type, current)
            return False
        return True

    def _move_from_jira(
        self, key: str, status: str, scope: tuple[str, str | None, str]
    ) -> None:
        """Read the transitions from Jira and move the ticket. Keep the list after a move that worked."""
        project, issue_type, current = scope
        live = self._live_transitions(key)
        chosen = _pick(status, live)
        if chosen is None:
            raise TrackerError(f"The workflow of {key} has no transition to {status}.")
        _refuse_done(key, status, chosen)
        self._post_transition(key, chosen)
        if issue_type is not None:
            self._metadata.store_transitions(project, issue_type, current, live)

    def _live_transitions(self, key: str) -> list[dict[str, Any]]:
        """Read the transitions of the ticket from Jira. Keep only the id and the target of each."""
        reply = self._http.call(
            "GET", f"{ISSUE_PATH}/{key}/{TRANSITIONS_SEGMENT}", shape=dict
        )
        with _expected_shape("the transitions"):
            return [
                {
                    "id": t["id"],
                    "to": {
                        "name": t["to"]["name"],
                        "statusCategory": {"key": t["to"]["statusCategory"]["key"]},
                    },
                }
                for t in reply["transitions"]
            ]

    def _post_transition(self, key: str, chosen: dict[str, Any]) -> None:
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
        cached = self._metadata.field_ids()
        if cached is not None:
            return cached
        wanted = set(CUSTOM_FIELD_NAMES.values())
        fields = self._http.call("GET", FIELD_PATH, shape=list)
        with _expected_shape("the list of fields"):
            ids = {f["name"]: f["id"] for f in fields if f.get("name") in wanted}
        self._metadata.store_field_ids(ids)
        return ids

    def _jql(self) -> str:
        projects = ", ".join(f'"{key}"' for key in self._settings.project_keys)
        return (
            f"project in ({projects}) "
            f'AND labels = "{self._settings.eligible_label}" '
            "AND statusCategory != Done AND assignee is EMPTY ORDER BY key ASC"
        )
