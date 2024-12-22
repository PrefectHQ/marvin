import asyncio
from typing import Annotated, TypedDict

import httpx
import turbopuffer as tpuf
from prefect import flow, task
from prefect.blocks.system import Secret
from prefect.cache_policies import NONE
from pydantic import AnyUrl, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.settings import ModelSettings
from raggy.vectorstores.tpuf import multi_query_tpuf

Observation = Annotated[str, Field(description="A single observation")]


class MainPoints(TypedDict):
    main_points: list[Observation]
    relevant_links: list[AnyUrl]


class DocsAgentContext(TypedDict):
    namespace: str
    user_objective: str


docs_agent = Agent[DocsAgentContext, MainPoints](
    "openai:gpt-4o",
    model_settings=ModelSettings(temperature=0),
    system_prompt=(
        "Summarize the query results into main points. "
        "Use the search tool to narrow in on terms related to the user's objective."
    ),
    result_type=MainPoints,
    deps_type=DocsAgentContext,
)


@docs_agent.tool  # type: ignore
@task(cache_policy=NONE)
def expanded_search(
    ctx: RunContext[DocsAgentContext],
    queries: list[str],
) -> str:
    """Expand a single given query to explore different facets of the query
    that are relevant to the user's objective.

    For example, given a question like:
    "how to get task run id from flow run"

    You might use the following queries:
    - "how to get task run id from flow run"
    - "retrieving metadata about the parent runtime context"
    - "what metadata is stored in Prefect?"
    - "what is available client side versus server side?"
    """
    return multi_query_tpuf(
        queries + [ctx.deps["user_objective"]],
        namespace=ctx.deps["namespace"],
        n_results=10,
    )


@flow(flow_run_name="run docs agent with {queries} in {namespace}")
async def run_docs_agent(
    queries: list[str], namespace: str, user_objective: str
) -> str:
    result = await docs_agent.run(
        user_prompt="\n\n".join(queries),
        deps={"namespace": namespace, "user_objective": user_objective},
    )
    return f"{result.data['main_points']}\n\n{result.data['relevant_links']}"


@task
def search_prefect_2x_docs(queries: list[str], hypothesized_user_objective: str) -> str:
    """Searches the Prefect documentation for the given queries.

    It is best to use more than one, short query to get the best results.

    For example, given a question like:
    "Is there a way to get the task_run_id for a task from a flow run?"

    You might use the following queries:
    - "retrieve task run id from flow run"
    - "retrieve run metadata dynamically"

    """
    if not tpuf.api_key:
        tpuf.api_key = Secret.load("tpuf-api-key", _sync=True).get()  # type: ignore

    return asyncio.run(
        run_docs_agent(queries, "prefect-2", hypothesized_user_objective)
    )


@task
def search_prefect_3x_docs(queries: list[str], hypothesized_user_objective: str) -> str:
    """Searches the Prefect documentation for the given queries.

    It is best to use more than one, short query to get the best results.

    For example, given a question like:
    "Is there a way to get the task_run_id for a task from a flow run?"

    You might use the following queries:
    - "retrieve task run id from flow run"

    """
    if not tpuf.api_key:
        tpuf.api_key = Secret.load("tpuf-api-key", _sync=True).get()  # type: ignore

    return asyncio.run(
        run_docs_agent(queries, "prefect-3", hypothesized_user_objective)
    )


@task
def search_controlflow_docs(
    queries: list[str], hypothesized_user_objective: str
) -> str:
    """Searches the ControlFlow documentation for the given queries.

    ControlFlow is an agentic framework built on top of Prefect 3.x.

    It is best to use more than one, short query to get the best results.
    """
    return asyncio.run(
        run_docs_agent(queries, "controlflow", hypothesized_user_objective)
    )


@task
def get_latest_prefect_release_notes() -> str:
    """Gets the latest Prefect release notes"""
    url = "https://api.github.com/repos/PrefectHQ/prefect/releases/latest"

    with httpx.Client() as client:
        response = client.get(url)
        release_notes = response.json().get("body")
        return release_notes
