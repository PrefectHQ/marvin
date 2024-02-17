import inspect
from typing import Literal

import httpx
import marvin
from marvin.tools.chroma import multi_query_chroma

Topic = Literal["latest_prefect_version"]


async def search_prefect_docs(queries: list[str]) -> str:
    """Searches the Prefect documentation for the given queries.

    It is best to use more than one, short query to get the best results.

    For example, given a question like:
    "Is there a way to get the task_run_id for a task from a flow run?"

    You might use the following queries:
    - "retrieve task run id from flow run"
    - "retrieve run metadata dynamically"

    """
    return await multi_query_chroma(queries=queries, n_results=3)


async def get_latest_release_notes() -> str:
    """Gets the first whole h2 section from the Prefect RELEASE_NOTES.md file."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://raw.githubusercontent.com/PrefectHQ/prefect/main/RELEASE-NOTES.md"
        )
        return response.text.split("\n## ")[1]


tool_map = {"latest_prefect_version": get_latest_release_notes}


async def get_info(topic: Topic) -> str:
    """A tool that returns information about a topic using
    one of many pre-existing helper functions. You need only
    provide the topic name, and the appropriate function will
    return information.

    As of now, the only topic is "latest_prefect_version".
    """

    try:
        maybe_coro = tool_map[topic]()
        if inspect.iscoroutine(maybe_coro):
            return await maybe_coro
        return maybe_coro
    except KeyError:
        raise ValueError(f"Invalid topic: {topic}")


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

        return f"{best_link}\n\n```python\n{code_example_content}\n```"
