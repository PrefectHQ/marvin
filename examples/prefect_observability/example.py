"""
Prefect + OpenAI Observability Example

This example demonstrates how to trace Marvin agent calls back to Prefect
flow and task runs in OpenAI's observability dashboard.

Run with:
    uv run example.py

Prerequisites:
    - OPENAI_API_KEY environment variable set
    - marvin[prefect] installed: uv add "marvin[prefect]"
"""

import asyncio

from prefect import flow, task

import marvin
from marvin.beta.observability.openai import get_prefect_context, observable

# Define your agent once, use it everywhere
analyst = marvin.Agent(
    name="analyst",
    model="openai:gpt-4o-mini",
    instructions="You are a helpful analyst. Be concise.",
)


@task
async def summarize(text: str) -> str:
    """Summarize the given text using AI."""
    # Wrap the agent to capture Prefect context
    # This is the key line - observable() captures flow_run_id, task_run_id, etc.
    return await observable(analyst).run_async(f"Summarize in one sentence: {text}")


@task
async def analyze_sentiment(text: str) -> str:
    """Analyze the sentiment of the given text."""
    return await observable(analyst).run_async(
        f"What is the sentiment of this text? Reply with one word: {text}"
    )


@flow(name="document-analysis")
async def analyze_document(document: str) -> dict:
    """
    Analyze a document using multiple AI tasks.

    Each task's AI call will be traceable back to this flow run in OpenAI logs.
    """
    # Get context for logging (not required, just for demonstration)
    ctx = get_prefect_context()
    print(f"\nFlow run: {ctx.get('prefect.flow_run.name')}")
    print(f"Flow run ID: {ctx.get('prefect.flow_run.id')}")

    # Run AI tasks
    summary = await summarize(document)
    sentiment = await analyze_sentiment(document)

    return {
        "summary": summary,
        "sentiment": sentiment,
        "flow_run_id": ctx.get("prefect.flow_run.id"),
    }


if __name__ == "__main__":
    # Example document to analyze
    document = """
    Prefect is a modern workflow orchestration tool that makes it easy to build,
    run, and monitor data pipelines. It provides a Python-native API for defining
    workflows as code, with built-in support for retries, caching, and observability.
    Teams love Prefect because it simplifies complex data engineering tasks while
    providing enterprise-grade reliability and monitoring capabilities.
    """

    print("=" * 60)
    print("Prefect + OpenAI Observability Example")
    print("=" * 60)

    # Run the flow
    result = asyncio.run(analyze_document(document))

    print("\nResults:")
    print(f"  Summary: {result['summary']}")
    print(f"  Sentiment: {result['sentiment']}")

    print("\n" + "=" * 60)
    print("View this request in OpenAI Platform:")
    print("  https://platform.openai.com/logs")
    print("")
    print("Filter by:")
    print(f"  prefect.flow_run.id = {result['flow_run_id']}")
    print("=" * 60)
