"""The guard of the settings table, the audit trail and the version counter

Revision ID: 0002_guards_and_audit
Revises: 0001_settings_tables
Create Date: 2026-10-29

The guard needs an actor for every write. The actor is not blank and has at most 200 characters.
It refuses a value that holds a secret. It scans every text of the value: the texts, the items of a list
and the keys of a map. It gives a repo row the type and the bounds of the org row of the same key.
The type, the bounds, the key and the scope of a row change only in a migration. A migration says so
with the session variable veil.migrating. An org row is added or removed only in a migration too.
Nobody can empty the table outside a migration.

The audit trigger writes who, when, the old value and the new value. A write that changes nothing writes
nothing. Nobody can change the audit table. Each change adds one to the version counter.

The secret patterns are the patterns of the Engine, written for PostgreSQL. A test checks that the table
refuses a sample of every kind. A new kind of secret needs a new migration.

This script holds its own SQL. It imports nothing of the code base, so it stays the same for ever.
"""

from alembic import op

revision = "0002_guards_and_audit"
down_revision = "0001_settings_tables"
branch_labels = None
depends_on = None

guard_sql = r"""
CREATE FUNCTION settings_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    actor text := nullif(btrim(coalesce(current_setting('veil.actor', true), ''), E' \t\r\n'), '');
    migrating boolean := coalesce(current_setting('veil.migrating', true), '') = 'on';
    org_row settings%ROWTYPE;
    secret_pattern text;
    scanned text;
BEGIN
    IF actor IS NULL THEN
        RAISE EXCEPTION 'A write to the settings needs an actor. Set veil.actor first.';
    END IF;
    IF length(actor) > 200 THEN
        RAISE EXCEPTION 'The actor has more than 200 characters.';
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.scope = 'org' AND NOT migrating THEN
            RAISE EXCEPTION 'An org row can only be removed in a migration.';
        END IF;
        RETURN OLD;
    END IF;
    IF TG_OP = 'INSERT' AND NEW.scope = 'org' AND NOT migrating THEN
        RAISE EXCEPTION 'An org row can only be added in a migration.';
    END IF;
    IF TG_OP = 'UPDATE' AND NOT migrating AND
       (NEW.scope, NEW.key, NEW.type, NEW.min_value, NEW.max_value)
       IS DISTINCT FROM (OLD.scope, OLD.key, OLD.type, OLD.min_value, OLD.max_value) THEN
        RAISE EXCEPTION 'The scope, the key, the type and the bounds of a setting can only change in a migration.';
    END IF;
    scanned := coalesce(
        (SELECT string_agg(leaf #>> '{}', E'\n')
         FROM jsonb_path_query(NEW.value, 'strict $.**') AS leaf
         WHERE jsonb_typeof(leaf) = 'string'),
        ''
    ) || E'\n' || coalesce(
        (SELECT string_agg(map_key, E'\n')
         FROM jsonb_object_keys(
             CASE WHEN jsonb_typeof(NEW.value) = 'object' THEN NEW.value ELSE '{}'::jsonb END
         ) AS map_key),
        ''
    );
    FOREACH secret_pattern IN ARRAY ARRAY[
        '-----BEGIN ([A-Z]+ )*PRIVATE KEY-----',
        '\y(AKIA|ASIA)[0-9A-Z]{16}\y',
        '\ygh[pousr]_[A-Za-z0-9]{36,}\y',
        '\yAIza[0-9A-Za-z_-]{35}\y',
        '\yxox[abprs]-[A-Za-z0-9-]{10,}\y',
        '\ysk-[A-Za-z0-9_-]{20,}',
        '\yATATT3[A-Za-z0-9_=-]{20,}'
    ] LOOP
        IF scanned ~ secret_pattern THEN
            RAISE EXCEPTION 'A setting must not hold a secret.';
        END IF;
    END LOOP;
    IF NEW.scope <> 'org' THEN
        IF NEW.scope !~ '^repo:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$' THEN
            RAISE EXCEPTION 'The scope must be org or repo: and the name of one repo.';
        END IF;
        SELECT * INTO org_row FROM settings WHERE scope = 'org' AND key = NEW.key;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'The setting is not known. Only a setting with an org row can have a repo row.';
        END IF;
        NEW.type := org_row.type;
        NEW.min_value := org_row.min_value;
        NEW.max_value := org_row.max_value;
    END IF;
    NEW.updated_at := now();
    RETURN NEW;
END
$$
"""

truncate_sql = r"""
CREATE FUNCTION settings_truncate_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF nullif(btrim(coalesce(current_setting('veil.actor', true), ''), E' \t\r\n'), '') IS NULL THEN
        RAISE EXCEPTION 'A write to the settings needs an actor. Set veil.actor first.';
    END IF;
    IF coalesce(current_setting('veil.migrating', true), '') <> 'on' THEN
        RAISE EXCEPTION 'The settings table can only be emptied in a migration.';
    END IF;
    RETURN NULL;
END
$$
"""

audit_sql = r"""
CREATE FUNCTION settings_audit_write() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND (OLD.value, OLD.type, OLD.min_value, OLD.max_value)
           IS NOT DISTINCT FROM (NEW.value, NEW.type, NEW.min_value, NEW.max_value) THEN
        RETURN NULL;
    END IF;
    INSERT INTO settings_audit (actor, action, scope, key, old_value, new_value)
    VALUES (
        btrim(current_setting('veil.actor', true), E' \t\r\n'),
        lower(TG_OP),
        coalesce(NEW.scope, OLD.scope),
        coalesce(NEW.key, OLD.key),
        CASE WHEN TG_OP <> 'INSERT' THEN OLD.value END,
        CASE WHEN TG_OP <> 'DELETE' THEN NEW.value END
    );
    UPDATE settings_version SET version = version + 1 WHERE id;
    RETURN NULL;
END
$$
"""

append_only_sql = r"""
CREATE FUNCTION settings_audit_keep() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'The audit trail of the settings cannot be changed.';
END
$$
"""


def upgrade() -> None:
    op.execute(guard_sql)
    op.execute(truncate_sql)
    op.execute(audit_sql)
    op.execute(append_only_sql)
    op.execute(
        "CREATE TRIGGER settings_guard BEFORE INSERT OR UPDATE OR DELETE ON settings "
        "FOR EACH ROW EXECUTE FUNCTION settings_guard()"
    )
    op.execute(
        "CREATE TRIGGER settings_truncate_guard BEFORE TRUNCATE ON settings "
        "FOR EACH STATEMENT EXECUTE FUNCTION settings_truncate_guard()"
    )
    op.execute(
        "CREATE TRIGGER settings_audit_write AFTER INSERT OR UPDATE OR DELETE ON settings "
        "FOR EACH ROW EXECUTE FUNCTION settings_audit_write()"
    )
    op.execute(
        "CREATE TRIGGER settings_audit_keep BEFORE UPDATE OR DELETE ON settings_audit "
        "FOR EACH ROW EXECUTE FUNCTION settings_audit_keep()"
    )
    op.execute(
        "CREATE TRIGGER settings_audit_keep_all BEFORE TRUNCATE ON settings_audit "
        "FOR EACH STATEMENT EXECUTE FUNCTION settings_audit_keep()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER settings_audit_keep_all ON settings_audit")
    op.execute("DROP TRIGGER settings_audit_keep ON settings_audit")
    op.execute("DROP TRIGGER settings_audit_write ON settings")
    op.execute("DROP TRIGGER settings_truncate_guard ON settings")
    op.execute("DROP TRIGGER settings_guard ON settings")
    op.execute("DROP FUNCTION settings_audit_keep()")
    op.execute("DROP FUNCTION settings_audit_write()")
    op.execute("DROP FUNCTION settings_truncate_guard()")
    op.execute("DROP FUNCTION settings_guard()")
