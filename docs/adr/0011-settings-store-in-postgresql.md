# The settings store in PostgreSQL

**Status: deferred.** veil runs on one repo through the GitHub Action now. GR-22. The code was removed with the service. The commit before the removal has it.

The org-wide service reads its settings from PostgreSQL (ticket GR-22, decision GR-11). The code is in `veil/adapters/postgres/`. The Engine does not change. It still gets a `Settings` object.

## What we decided

- **One table.** `settings` has a scope, a key, a value, a type, a minimum and a maximum. The scope is `org` or `repo:owner/name`. So the org layer and the repo layer share one table. The value is JSON.
- **The table keeps the rules.** A value must match its type. A number must be whole and inside the bounds. A trigger gives a repo row the type and the bounds of the org row of the same key. So a repo row cannot widen the bounds, and the table refuses a repo row for an unknown key. A repo scope names one repo and never holds a star.
- **No secrets.** A trigger scans every text of the value: the texts, the items of a list and the keys of a map. It scans the real text, so a secret after a line break or a tab does not escape. It refuses a text that matches a secret pattern. The patterns are the patterns of the Engine, written for PostgreSQL. A test checks that the table refuses a sample of every kind.
- **The structure needs a migration.** The type, the bounds, the key and the scope of a row change only in a migration. Only a migration can add or remove an org row. Nobody can empty the table outside a migration. A migration says so with the session variable `veil.migrating`. So a new setting always comes with a migration, and the seed always matches the catalog.
- **The audit trail.** Every insert, update and removal writes a row to `settings_audit`: who, when, the old value and the new value. A write that changes nothing writes nothing. A change of the bounds by a migration shows as an update with the same old and new value. Nobody can change or remove an audit row.
- **The actor.** The table refuses a write with no actor, a blank actor and an actor of more than 200 characters. The writer gives the actor in the transaction (`veil.actor`).
- **The version counter.** One row counts the changes. A snapshot carries the number. The Redis cache of GR-23 puts it in its key, so a change makes the old entry stale at once. A write that changes nothing does not count.
- **Migrations.** Alembic applies versioned scripts, as the gozu service does. The scripts are hand-written SQL. A script holds its own SQL and its own data and imports nothing of the code. So it stays the same for ever. All changes of one call run in one transaction. Two deployments that migrate at the same time take turns with a database lock. A test applies every migration to an empty database and undoes them again.
- **Deployment.** Deployment runs `python -m veil.adapters.postgres.migrate` with the variable `VEIL_DATABASE_URL`. A Shell can call `apply_migrations(engine)` instead. The program of Alembic works too, with `alembic.ini` in the same folder.
- **The models.** The SQLAlchemy models describe the columns and the keys. The migrations hold the checks and the triggers, and tests of the real database prove them. A test compares the models with the migrated columns.
- **The seed.** Migration 3 inserts one org row for every setting, with its default and its bounds from the catalog. The rows are frozen in the script. A test compares the seeded rows with the catalog. When the catalog changes, the test fails until a new migration exists.
- **What the seed means.** Every key has an org row. So in the service a repo can only tighten the default, and a locked value stays locked. A repo file cannot set the Jira site. This closes the risk that ADR 0010 named for GR-25.
- **The reader.** `read_snapshot(repos)` reads the version, the org rows and the rows of the given repos in one read-only transaction at the isolation level `REPEATABLE READ`. It gives a frozen `SettingsSnapshot`. `settings_for(repo, overrides)` calls `resolve_settings`, so the layers and the rules for a repo are the same as everywhere. A setting with no row keeps its code default.
- **A snapshot is plain data.** A workflow can carry it. A retried activity then uses the same values. A change in the database applies to the next snapshot only.
- **The writer.** `set_org`, `set_repo` and `clear_repo` check the value with the schema first. The writer keeps the exact JSON kind of a setting, so the text `2` is not a number. A repo value must pass the rule for a repo against the org row. A change of an org value must not loosen any repo row. If it would, the writer refuses it and names the repo.
- **The writer takes turns.** A write locks the org row of its setting. A change of the org value and a change of a repo value for the same setting wait for each other. So a repo row cannot slip past a new org value.
- **The credentials.** The Shell passes an engine. The URL and the password of the database are not settings.

## What we accept for now

- The snapshot holds all org rows and the rows of the repos that the caller names. A repo that the caller did not name is an error, and not a silent org value.
- The owner of the database can switch the triggers off. We trust the owner. A check on the schema is the job of the operators.
- The actor is text. The table does not bind it to the database user. The Shell must pass a real name.
- A new secret pattern in the Engine needs a new migration for the table. The test for the samples fails until it exists.
- Two writers at the same time wait for each other on the version row.
- The store has three jobs: the reader, the writer and the clearing of a repo row. It is still short. We split it when it grows.
- The tests need PostgreSQL programs on the machine, or the variable `VEIL_TEST_DATABASE_URL`. Without them, the tests skip.
- No test ran against the PostgreSQL service on AWS.
