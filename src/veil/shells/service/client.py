from temporalio.client import Client, WorkflowHandle
from temporalio.common import WorkflowIDConflictPolicy

from veil.engine.models.report.run_report import RunReport
from veil.shells.service.constants.names import TASK_QUEUE
from veil.shells.service.workflow import RepoRunWorkflow
from veil.shells.service.workflow_id import workflow_id


async def start_repo_run(
    client: Client, repo: str, task_queue: str = TASK_QUEUE
) -> WorkflowHandle[RepoRunWorkflow, RunReport]:
    """Start the run for a repo. If a run for the repo is active, return its handle and start no second run."""
    return await client.start_workflow(
        RepoRunWorkflow.run,
        repo,
        id=workflow_id(repo),
        task_queue=task_queue,
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
    )
