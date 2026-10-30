import asyncio
import os
import time

import pytest
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from tests.shells.github_action.support import SITE
from tests.shells.service.support import FakeEngine, make_deps, reports
from veil.adapters.postgres.store import PostgresSettingsStore
from veil.shells.service.temporal.worker import create_worker


@pytest.fixture
def store(engine):
    store = PostgresSettingsStore(engine)
    store.set_org("jira_site_url", SITE, actor="test")
    return store


def old_folder(root, name, age_minutes):
    folder = root / name
    folder.mkdir(parents=True)
    stamp = time.time() - age_minutes * 60
    os.utime(folder, (stamp, stamp))
    return folder


def start(temporal_host, deps):
    async def main():
        client = await Client.connect(
            temporal_host, data_converter=pydantic_data_converter
        )
        return create_worker(client, deps, run=FakeEngine(reports()))

    return asyncio.run(main())


def test_a_new_worker_deletes_the_checkouts_older_than_one_hour(
    temporal_host, tmp_path, stubs, store
):
    deps = make_deps(tmp_path, stubs, settings_source=store)
    old = old_folder(deps.checkout_root, "old", 90)
    new = old_folder(deps.checkout_root, "new", 10)

    start(temporal_host, deps)

    assert not old.exists()
    assert new.exists()


def test_the_age_limit_is_the_org_setting(temporal_host, tmp_path, stubs, store):
    store.set_org("checkout_sweep_minutes", 15, actor="test")
    deps = make_deps(tmp_path, stubs, settings_source=store)
    folder = old_folder(deps.checkout_root, "twenty", 20)

    start(temporal_host, deps)

    assert not folder.exists()
