from typing import Literal

import httpx
import marvin
import turbopuffer as tpuf
from prefect import task
from prefect.blocks.system import Secret
from raggy.vectorstores.tpuf import multi_query_tpuf

Topic = Literal["latest_prefect_version"]


@task
async def search_prefect_2x_docs(queries: list[str]) -> str:
    """Searches the Prefect documentation for the given queries.

    It is best to use more than one, short query to get the best results.

    For example, given a question like:
    "Is there a way to get the task_run_id for a task from a flow run?"

    You might use the following queries:
    - "retrieve task run id from flow run"
    - "retrieve run metadata dynamically"

    """
    if not tpuf.api_key:
        tpuf.api_key = (await Secret.load("tpuf-api-key")).get()  # type: ignore

    return await multi_query_tpuf(queries, namespace="prefect-2")


@task
async def search_prefect_3x_docs(queries: list[str]) -> str:
    """Searches the Prefect documentation for the given queries.

    It is best to use more than one, short query to get the best results.

    For example, given a question like:
    "Is there a way to get the task_run_id for a task from a flow run?"

    You might use the following queries:
    - "retrieve task run id from flow run"

    """
    if not tpuf.api_key:
        tpuf.api_key = (await Secret.load("tpuf-api-key")).get()  # type: ignore

    return await multi_query_tpuf(queries, namespace="prefect-3")


async def get_prefect_code_example(related_to: str) -> str:
    """Gets a Prefect code example"""

    base_url = "https://raw.githubusercontent.com/zzstoatzz/prefect-code-examples/main"

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/views/README.json")

        example_items = {
            item.get("description"): item.get("relative_path")
            for category in response.json().get("categories", [])
            for item in category.get("examples", [])
        }

        key = await marvin.classify_async(
            data=related_to, labels=list(example_items.keys())
        )

        best_link = f"{base_url}/{example_items[key]}"

        code_example_content = (await client.get(best_link)).text

        return f"LINK:\n{best_link}\n\n EXAMPLE:\n{code_example_content}"
