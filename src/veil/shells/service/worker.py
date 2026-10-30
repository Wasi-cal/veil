from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from temporalio.client import Client
from temporalio.worker import Worker

from veil.engine.context import Context
from veil.engine.models.report.run_report import RunReport
from veil.engine.run import run as run_engine
from veil.shells.service.activities import EngineActivities
from veil.shells.service.checkout_sweep import sweep_old_checkouts
from veil.shells.service.constants.names import ACTIVITY_THREADS, TASK_QUEUE
from veil.shells.service.models.service_dependencies import ServiceDependencies
from veil.shells.service.workflow import RepoRunWorkflow


def create_worker(
    client: Client,
    dependencies: ServiceDependencies,
    run: Callable[[Context], RunReport] = run_engine,
    task_queue: str = TASK_QUEUE,
) -> Worker:
    """Build the worker of the service. First delete the old checkouts that a crash left behind.

    The age limit is the org setting `checkout_sweep_minutes`.
    """
    org = dependencies.settings_source.read_snapshot().settings_for()
    sweep_old_checkouts(
        dependencies.checkout_root, timedelta(minutes=org.checkout_sweep_minutes)
    )
    activities = EngineActivities(dependencies, run=run)
    return Worker(
        client,
        task_queue=task_queue,
        workflows=[RepoRunWorkflow],
        activities=[activities.read_settings, activities.run_engine],
        activity_executor=ThreadPoolExecutor(max_workers=ACTIVITY_THREADS),
        max_concurrent_activities=ACTIVITY_THREADS,
    )
