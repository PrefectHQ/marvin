import httpx
import turbopuffer as tpuf
from modules import ModuleTreeExplorer
from prefect import task
from prefect.blocks.system import Secret
from raggy.vectorstores.tpuf import multi_query_tpuf


@task
def review_top_level_prefect_api() -> str:
    """
    Review the available submodules and the top-level API of Prefect.
    """
    explorer = ModuleTreeExplorer("prefect", max_depth=0)
    explorer.explore()
    return explorer.get_tree_string()


@task
def review_common_3x_gotchas() -> list[str]:
    """If needed, review common sources of confusion for Prefect 3.x users."""
    return [
        ".map and .submit are always synchronous, even if the underlying function is asynchronous",
        "futures returned by .map can be resolved together, like integers = double.map(range(10)).result()",
        "futures must be resolved by passing them to another task, returning them or manually calling .result() or .wait()",
        "agents are replaced by workers in prefect 3.x, work pools replace the infra blocks from prefect.infrastructure",
        "prefect 3.x uses pydantic 2 and server data from prefect 2.x is not compatible with 3.x",
        "Deployment.build_from_flow() is removed in 3.x, use some_flow.from_source(...).deploy(...) instead.",
    ]


@task
def explore_module_offerings(module_path: str, max_depth: int = 1) -> str:
    """
    Explore and return the public API tree of a specific module and its submodules as a string.

    Args:
        module_path: String representing the module path (e.g., 'prefect.runtime')
        max_depth: Maximum depth to explore in the module tree (default: 2)

    Returns:
        str: A formatted string representation of the module tree

    Example:
        >>> explore_module_tree('prefect.runtime', max_depth=0)
    """
    explorer = ModuleTreeExplorer(module_path, max_depth)
    explorer.explore()
    return explorer.get_tree_string()


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
        tpuf.api_key = Secret.load("tpuf-api-key", _sync=True).get()  # type: ignore

    return multi_query_tpuf(queries, namespace="prefect-2", n_results=5)


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
        tpuf.api_key = Secret.load("tpuf-api-key", _sync=True).get()  # type: ignore

    return multi_query_tpuf(queries, namespace="prefect-3", n_results=5)


@task
def search_controlflow_docs(queries: list[str]) -> str:
    """Searches the ControlFlow documentation for the given queries.

    ControlFlow is an agentic framework built on top of Prefect 3.x.

    It is best to use more than one, short query to get the best results.
    """
    return multi_query_tpuf(queries, namespace="controlflow", n_results=5)


@task
def get_latest_prefect_release_notes() -> str:
    """Gets the latest Prefect release notes"""
    url = "https://api.github.com/repos/PrefectHQ/prefect/releases/latest"

    with httpx.Client() as client:
        response = client.get(url)
        release_notes = response.json().get("body")
        return release_notes
