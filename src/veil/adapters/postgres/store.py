import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from functools import cache
from typing import Any

from sqlalchemy import Engine, or_, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from veil.adapters.postgres.constants.database import SNAPSHOT_ISOLATION_LEVEL
from veil.adapters.postgres.constants.scopes import (
    ACTOR_VARIABLE,
    ORG_SCOPE,
    REPO_NAME_PATTERN,
    REPO_SCOPE_PREFIX,
)
from veil.adapters.postgres.models.settings_snapshot import SettingsSnapshot
from veil.adapters.postgres.orm import SettingRow, SettingsVersionRow
from veil.engine import resolve_settings, settings_catalog
from veil.engine.constants.settings_messages import (
    LAYER_ORG,
    LAYER_REPO,
    MUST_BE_LIST,
    MUST_BE_TEXT,
    MUST_BE_TRUE_OR_FALSE,
    MUST_BE_WHOLE_NUMBER,
)
from veil.engine.errors.settings_error import SettingsError


class PostgresSettingsStore:
    """The settings in PostgreSQL. The service reads one snapshot at the start of a run.

    The table checks the type and the bounds and refuses a secret. The store also checks every value
    with the schema, and a repo value with the rule for a repo, before the database sees it.
    A write locks the org row of its setting, so a change of the org value and a change of a repo value
    take turns. Every write names an actor. The database records who, when, the old value and the new value.
    The credentials of the database come with the engine. They are never settings.
    """

    def __init__(self, engine: Engine):
        self._engine = engine

    def read_snapshot(self, repos: Sequence[str] = ()) -> SettingsSnapshot:
        """Read the org rows and the rows of these repos, and the version, at one point in time."""
        for repo in repos:
            _check_repo(repo)
        scopes = [REPO_SCOPE_PREFIX + repo for repo in repos]
        connection = self._engine.connect().execution_options(
            isolation_level=SNAPSHOT_ISOLATION_LEVEL, postgresql_readonly=True
        )
        with connection, Session(connection) as session:
            version = session.execute(select(SettingsVersionRow.version)).scalar_one()
            rows = session.scalars(
                select(SettingRow).where(
                    or_(SettingRow.scope == ORG_SCOPE, SettingRow.scope.in_(scopes))
                )
            ).all()
        org = {row.key: row.value for row in rows if row.scope == ORG_SCOPE}
        by_repo = {
            repo: {
                row.key: row.value
                for row in rows
                if row.scope == REPO_SCOPE_PREFIX + repo
            }
            for repo in repos
        }
        return SettingsSnapshot(version=version, org=org, repos=by_repo)

    def set_org(self, key: str, value: Any, actor: str) -> None:
        """Change the org value of a setting.

        Raise SettingsError if the schema refuses the value, or if the new value would loosen a repo row.
        """
        resolve_settings(org={key: value})
        _check_kind(LAYER_ORG, key, value)
        with self._transaction(actor) as session:
            row = session.get(SettingRow, (ORG_SCOPE, key), with_for_update=True)
            if row is None:
                raise _missing_org_row(key)
            loosened = [
                repo_row.scope.removeprefix(REPO_SCOPE_PREFIX)
                for repo_row in session.scalars(
                    select(SettingRow).where(
                        SettingRow.key == key, SettingRow.scope != ORG_SCOPE
                    )
                )
                if _loosens(key, value, repo_row.value)
            ]
            if loosened:
                raise SettingsError(
                    [
                        f"{LAYER_ORG}: the new value of {key} would loosen the value of the repo {repo}."
                        for repo in loosened
                    ]
                )
            row.value = value

    def set_repo(self, repo: str, key: str, value: Any, actor: str) -> None:
        """Set a value for one repo. Raise SettingsError if it is not a tighter value than the org value."""
        _check_repo(repo)
        with self._transaction(actor) as session:
            org = session.get(
                SettingRow, (ORG_SCOPE, key), with_for_update={"read": True}
            )
            if org is None:
                raise _missing_org_row(key)
            resolve_settings(org={key: org.value}, repo={key: value})
            _check_kind(LAYER_REPO, key, value)
            scope = REPO_SCOPE_PREFIX + repo
            row = session.get(SettingRow, (scope, key))
            if row is None:
                session.add(
                    SettingRow(
                        scope=scope,
                        key=key,
                        value=value,
                        type=org.type,
                        min_value=org.min_value,
                        max_value=org.max_value,
                    )
                )
            else:
                row.value = value

    def clear_repo(self, repo: str, key: str, actor: str) -> None:
        """Remove the repo value of a setting. The org value applies again."""
        _check_repo(repo)
        with self._transaction(actor) as session:
            row = session.get(SettingRow, (REPO_SCOPE_PREFIX + repo, key))
            if row is not None:
                session.delete(row)

    @contextmanager
    def _transaction(self, actor: str) -> Iterator[Session]:
        """One transaction that names its actor. A database refusal becomes a SettingsError with no value in it."""
        if not actor.strip():
            raise ValueError("A write to the settings needs an actor.")
        session = Session(self._engine)
        try:
            session.execute(
                text("SELECT set_config(:name, :actor, true)"),
                {"name": ACTOR_VARIABLE, "actor": actor},
            )
            yield session
            session.commit()
        except DBAPIError:
            session.rollback()
            raise SettingsError(["The database refused the write."]) from None
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()


def _missing_org_row(key: str) -> SettingsError:
    return SettingsError(
        [f"The org row of {key} is missing. A migration must seed it."]
    )


def _loosens(key: str, org_value: Any, repo_value: Any) -> bool:
    """Say if the repo value would be looser than this org value."""
    try:
        resolve_settings(org={key: org_value}, repo={key: repo_value})
    except SettingsError:
        return True
    return False


@cache
def _value_types() -> dict[str, str]:
    return {entry.key: entry.value_type for entry in settings_catalog()}


def _check_kind(layer: str, key: str, value: Any) -> None:
    """Keep the exact JSON kind of a setting. The schema takes the text 2 for a number, and the table does not."""
    kind = _value_types()[key]
    ok = {
        "int": isinstance(value, int) and not isinstance(value, bool),
        "str": isinstance(value, str),
        "bool": isinstance(value, bool),
        "list": isinstance(value, list | tuple),
        "map": isinstance(value, dict),
    }[kind]
    if not ok:
        words = {
            "int": MUST_BE_WHOLE_NUMBER,
            "str": MUST_BE_TEXT,
            "bool": MUST_BE_TRUE_OR_FALSE,
            "list": MUST_BE_LIST,
            "map": "must be a map",
        }[kind]
        raise SettingsError([f"{layer}: {key} {words}."])


def _check_repo(repo: str) -> None:
    if not re.fullmatch(REPO_NAME_PATTERN, repo):
        raise SettingsError(["The repo name must be owner/name."])
