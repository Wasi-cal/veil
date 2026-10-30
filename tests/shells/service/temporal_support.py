import asyncio
import base64
import json
import uuid
from collections.abc import Awaitable, Callable

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from veil.shells.service.worker import create_worker


def with_worker(host, deps, engine, scenario: Callable[..., Awaitable]):
    """Run `scenario(client, task_queue)` while a worker of the service runs. Return what it returns."""

    async def main():
        client = await Client.connect(host, data_converter=pydantic_data_converter)
        task_queue = f"test-{uuid.uuid4().hex}"
        worker = create_worker(client, deps, run=engine, task_queue=task_queue)
        async with worker:
            return await scenario(client, task_queue)

    return asyncio.run(main())


def history_text(history) -> str:
    """All the text in a workflow history. A payload is decoded, so a secret in it shows."""
    pieces: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            pieces.append(node)
            try:
                pieces.append(base64.b64decode(node, validate=True).decode())
            except Exception:  # noqa: BLE001, S110
                pass

    walk(json.loads(history.to_json()))
    return "\n".join(pieces)


def activity_scheduled(history, name: str):
    """The attributes of the first 'activity scheduled' event for this activity."""
    for event in history.events:
        attributes = event.activity_task_scheduled_event_attributes
        if event.HasField("activity_task_scheduled_event_attributes") and (
            attributes.activity_type.name == name
        ):
            return attributes
    raise AssertionError(f"No activity {name} was scheduled.")
