# Prefect + OpenAI Observability

> **Note:** This is a beta feature (`marvin.beta.observability.openai`) and only
> works with OpenAI models.

This example shows how to trace Marvin agent calls back to Prefect flow and task
runs in OpenAI's observability dashboard.

## Why?

When running AI workloads in production with Prefect, you often want to answer
questions like:

- "Which flow run made this expensive GPT-4 call?"
- "How much did AI inference cost for deployment X last week?"
- "Why did this task fail? What did the AI actually return?"

This integration automatically captures Prefect runtime context (flow_run_id,
task_run_id, deployment name, etc.) and sends it to OpenAI as request metadata.
You can then filter and search in OpenAI's logs dashboard.

## Installation

```bash
uv add "marvin[prefect]"
```

Or with pip:

```bash
pip install "marvin[prefect]"
```

## Usage

The main function is `observable()`. Wrap your agent with it inside a Prefect
task to capture the current context:

```python
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
```

## What gets captured

When you call `observable(agent)` inside a Prefect run:

| Metadata Key | Example Value | Description |
|--------------|---------------|-------------|
| `prefect.flow_run.id` | `abc-123-def` | UUID of the flow run |
| `prefect.flow_run.name` | `happy-tiger` | Human-readable run name |
| `prefect.flow_run.flow_name` | `my-pipeline` | Name of the flow |
| `prefect.task_run.id` | `xyz-789` | UUID of the task run |
| `prefect.task_run.name` | `summarize-0` | Human-readable task run name |
| `prefect.task_run.task_name` | `summarize` | Name of the task function |
| `prefect.deployment.id` | `dep-456` | Deployment UUID (if deployed) |
| `prefect.deployment.name` | `prod-pipeline` | Deployment name (if deployed) |

## Viewing in OpenAI

1. Run your flow
2. Go to https://platform.openai.com/logs
3. Filter by any metadata field, e.g., `prefect.flow_run.id = abc-123-def`

## Running this example

```bash
cd examples/prefect_observability
uv run example.py
```

The script will print the flow_run_id at the end - use that to find the request
in OpenAI's logs.

## Advanced: Custom metadata

If you need to add business-specific metadata:

```python
@task
async def process(customer_id: str, text: str) -> str:
    return await observable(agent, customer_id=customer_id).run_async(text)
```

All custom metadata is merged with the Prefect context.
