"""
OpenAI observability integration.

This module enables tracing Marvin agent calls to OpenAI's observability dashboard.
When running inside Prefect flows/tasks, it automatically captures runtime context
(flow_run_id, task_run_id, etc.) and sends it as request metadata.

## Installation

    uv add "marvin[prefect]"

Or with pip:

    pip install "marvin[prefect]"

## Usage

The main function is `observable()`. Call it on an agent inside a Prefect task
to automatically capture the current runtime context:

    from prefect import flow, task
    import marvin
    from marvin.beta.observability.openai import observable

    agent = marvin.Agent(name="analyst", model="openai:gpt-4o")

    @task
    async def summarize(text: str) -> str:
        return await observable(agent).run_async(f"Summarize: {text}")

    @flow
    async def my_pipeline(document: str):
        return await summarize(document)

## What gets captured

When you call `observable(agent)` inside a Prefect run, the following metadata
is automatically sent to OpenAI:

- `prefect.flow_run.id` - UUID of the flow run
- `prefect.flow_run.name` - Human-readable name (e.g., "happy-tiger")
- `prefect.flow_run.flow_name` - Name of the flow function
- `prefect.task_run.id` - UUID of the task run (if inside a task)
- `prefect.task_run.name` - Human-readable task run name
- `prefect.task_run.task_name` - Name of the task function
- `prefect.deployment.id` - Deployment UUID (if deployed)
- `prefect.deployment.name` - Deployment name (if deployed)

## Viewing in OpenAI

After running your flow, view the requests at:
https://platform.openai.com/logs

Filter by any of the metadata fields above, e.g.:
- Filter by `prefect.flow_run.id` to see all AI calls from one flow run
- Filter by `prefect.task_run.task_name` to see calls from a specific task type

## Advanced: Custom metadata

If you need to add additional metadata beyond what Prefect provides:

    @task
    async def process(customer_id: str, text: str) -> str:
        return await observable(agent, customer_id=customer_id).run_async(text)

Custom metadata is merged with the Prefect context. All values must be strings.

## Note

This module is in beta and only works with OpenAI models. The metadata is sent
via OpenAI's stored completions feature (store=True).
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from marvin import Agent


def observable(agent: "Agent", **metadata: str) -> "Agent":
    """
    Enable OpenAI observability for this agent.

    Returns a new agent that automatically captures Prefect runtime context
    (flow_run_id, task_run_id, deployment info) and sends it to OpenAI's
    observability logs.

    Call this inside a Prefect task or flow to capture the current context:

        @task
        async def my_task():
            return await observable(agent).run_async("hello")

    Args:
        agent: The Marvin agent to make observable.
        **metadata: Optional extra metadata to include (e.g., customer_id="abc").
                   All values must be strings.

    Returns:
        A new agent with observability enabled. The original agent is unchanged.

    Note:
        This only works with OpenAI models. The metadata is sent via OpenAI's
        stored completions feature (store=True).
    """
    settings = _build_openai_settings(metadata)
    merged = _deep_merge(dict(agent.model_settings), settings)
    return dataclasses.replace(agent, model_settings=merged)


def get_prefect_context() -> dict[str, str]:
    """
    Get current Prefect runtime context as a flat dict.

    Returns metadata about the current flow run, task run, and deployment.
    Returns empty dict if not inside a Prefect flow or if Prefect is not installed.

    This is useful for debugging or if you need direct access to the context.
    Most users should just use `observable()` instead.
    """
    try:
        from prefect import runtime

        if runtime.flow_run.id is None:
            return {}

        ctx: dict[str, Any] = {
            "prefect.flow_run.id": runtime.flow_run.id,
            "prefect.flow_run.name": runtime.flow_run.name,
            "prefect.flow_run.flow_name": runtime.flow_run.flow_name,
            "prefect.deployment.id": runtime.deployment.id,
            "prefect.deployment.name": runtime.deployment.name,
            "prefect.task_run.id": runtime.task_run.id,
            "prefect.task_run.name": runtime.task_run.name,
            "prefect.task_run.task_name": runtime.task_run.task_name,
        }

        return {k: str(v) for k, v in ctx.items() if v is not None}

    except ImportError:
        return {}
    except Exception:
        return {}


def openai_request_kwargs(**metadata: str) -> dict[str, Any]:
    """
    Build kwargs for direct OpenAI SDK calls (without Marvin).

    Use this if you're calling the OpenAI SDK directly:

        from openai import AsyncOpenAI
        from marvin.beta.observability.openai import openai_request_kwargs

        client = AsyncOpenAI()

        @task
        async def generate(prompt: str) -> str:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                **openai_request_kwargs(),
            )
            return response.choices[0].message.content

    Args:
        **metadata: Optional extra metadata to include.

    Returns:
        Dict with `store` and `metadata` keys for OpenAI API calls.
    """
    combined = get_prefect_context()
    combined.update(metadata)

    result: dict[str, Any] = {"store": True}
    if combined:
        result["metadata"] = combined
    return result


def _build_openai_settings(extra_metadata: dict[str, str]) -> dict[str, Any]:
    """Build model_settings dict for OpenAI observability."""
    metadata = get_prefect_context()
    metadata.update(extra_metadata)

    if not metadata:
        return {"extra_body": {"store": True}}

    return {
        "extra_body": {
            "store": True,
            "metadata": metadata,
        }
    }


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dicts, with override taking precedence."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


__all__ = [
    "get_prefect_context",
    "observable",
    "openai_request_kwargs",
]
