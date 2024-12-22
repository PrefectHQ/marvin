from typing import Literal

import httpx
import turbopuffer as tpuf
from prefect import task
from prefect.blocks.system import Secret
from raggy.vectorstores.tpuf import multi_query_tpuf

Topic = Literal["latest_prefect_version"]


@task
def search_prefect_2x_docs(queries: list[str]) -> str:
    """Searches the Prefect documentation for the given queries.

    It is best to use more than one, short query to get the best results.

    For example, given a question like:
    "Is there a way to get the task_run_id for a task from a flow run?"

    You might use the following queries:
    - "retrieve task run id from flow run"
    - "retrieve run metadata dynamically"

    """
    if not tpuf.api_key:
        tpuf.api_key = Secret.load("tpuf-api-key").get()  # type: ignore

    return multi_query_tpuf(queries, namespace="prefect-2")


@task
def search_prefect_3x_docs(queries: list[str]) -> str:
    """Searches the Prefect documentation for the given queries.

    It is best to use more than one, short query to get the best results.

    For example, given a question like:
    "Is there a way to get the task_run_id for a task from a flow run?"

    You might use the following queries:
    - "retrieve task run id from flow run"

    """
    if not tpuf.api_key:
        tpuf.api_key = Secret.load("tpuf-api-key").get()  # type: ignore

    return multi_query_tpuf(queries, namespace="prefect-3")


@task
def search_controlflow_docs(queries: list[str]) -> str:
    """Searches the ControlFlow documentation for the given queries.

    ControlFlow is an agentic framework built on top of Prefect 3.x.

    It is best to use more than one, short query to get the best results.
    """
    return multi_query_tpuf(queries, namespace="controlflow")


@task
def get_latest_prefect_release_notes() -> str:
    """Gets the latest Prefect release notes"""
    url = "https://api.github.com/repos/PrefectHQ/prefect/releases/latest"

    with httpx.Client() as client:
        response = client.get(url)
        release_notes = response.json().get("body")
        return release_notes
