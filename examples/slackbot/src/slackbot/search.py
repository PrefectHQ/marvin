import asyncio

import httpx
import turbopuffer as tpuf
from prefect import task
from prefect.blocks.system import Secret
from pretty_mod import display_signature
from pretty_mod.explorer import ModuleTreeExplorer
from raggy.vectorstores.tpuf import multi_query_tpuf

from slackbot.github import GitHubIssue, _get_token
from slackbot.settings import settings
from slackbot.strings import slice_tokens


def explore_module_offerings(module_path: str, max_depth: int = 1) -> str:
    """
    Explore and return the public API tree of a specific module and its submodules as a string.

    This is the primary tool for understanding what's available in Python modules.
    Use different max_depth values based on how deep you want to explore.

    Args:
        module_path: String representing the module path (e.g., 'prefect.runtime', 'json', 'pandas')
        max_depth: Maximum depth to explore in the module tree (default: 1)

    Returns:
        str: A formatted string representation of the module tree

    Common Examples:
        # Get top-level Prefect API overview
        >>> explore_module_offerings('prefect', max_depth=0)

        # Explore Prefect's runtime module in detail
        >>> explore_module_offerings('prefect.runtime', max_depth=2)

        # Quick overview of pandas structure
        >>> explore_module_offerings('pandas', max_depth=1)

        # See what's in a specific submodule
        >>> explore_module_offerings('prefect.artifacts', max_depth=0)
    """
    explorer = ModuleTreeExplorer(module_path, max_depth=max_depth)
    explorer.explore()
    summary = explorer.get_tree_string()
    print(summary)
    return summary


def review_common_3x_gotchas() -> list[str]:
    """If needed, review common sources of confusion for Prefect 3.x users."""
    tips = [
        "from_source('https://github.com/<owner>/<repo>') has replaced the GitHub block in Prefect 3.x",
        ".map and .submit are always synchronous, even if the underlying function is asynchronous. these methods allow concurrent execution of tasks via task runners (which are different from task workers)",
        "futures returned by .map can be resolved together, like integers = double.map(range(10)).result()",
        "futures must be resolved by passing them to another task, returning them or manually calling .result() or .wait()",
        "agents are replaced by workers in prefect 3.x, work pools replace the infra blocks from prefect.infrastructure",
        "the `prefect.infrastructure` IS COMPLETELY REMOVED IN 3.x, see work pools instead",
        "prefect 3.x uses pydantic 2 and server data from prefect 2.x is not compatible with 3.x",
        "Deployment.build_from_flow() IS COMPLETELY REMOVED IN 3.x, use some_flow.from_source(...).deploy(...) instead.",
        "`prefect deployment build ...`  IS COMPLETELY REMOVED IN 3.x, use `prefect deploy ...` instead",
        "Workers (f.k.a. agents) poll for scheduled runs, whereas task workers are websocket clients that executed backgrounded task runs",
        "To avoid interactivity in the Prefect CLI, use the TOP LEVEL --no-prompt flag, e.g. `prefect --no-prompt deploy ...`",
    ]
    print(tips)
    return tips


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

    print(f"Searching about {queries} in Prefect 2.x docs")

    return multi_query_tpuf(queries, namespace="prefect-2", n_results=5)


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

    print(f"Searching about {queries} in Prefect 3.x docs")

    return multi_query_tpuf(queries, namespace="prefect-3", n_results=5)


def search_marvin_docs(queries: list[str]) -> str:
    """Searches the Marvin documentation for the given queries.

    Marvin is an agentic framework built on top of pydantic-ai.

    It is best to use more than one, short query to get the best results.
    """
    return multi_query_tpuf(queries, namespace="marvin", n_results=5)


def get_latest_prefect_release_notes() -> str:
    """Gets the latest Prefect release notes"""
    url = "https://api.github.com/repos/PrefectHQ/prefect/releases/latest"

    print(f"Getting latest Prefect release notes from {url}")

    with httpx.Client() as client:
        response = client.get(url)
        release_notes = response.json().get("body")
        return release_notes


@task(task_run_name="Reading {n} issues from {repo} given query: {query}")
def read_github_issues(query: str, repo: str = "prefecthq/prefect", n: int = 3) -> str:
    """
    Use the GitHub API to search for issues in a given repository. Do
    not alter the default value for `n` unless specifically requested by
    a user.

    For example, to search for open issues about AttributeErrors with the
    label "bug" in PrefectHQ/prefect:
        - repo: prefecthq/prefect
        - query: label:bug is:open AttributeError
    """
    github_token = Secret.load(settings.github_token_secret_name, _sync=True).get()  # type: ignore
    return asyncio.run(
        search_github_issues(query, repo=repo, n=n, api_token=github_token)
    )


async def search_github_issues(
    query: str,
    repo: str = "prefecthq/prefect",
    n: int = 3,
    api_token: str | None = None,
) -> str:
    """
    Use the GitHub API to search for issues in a given repository. Do
    not alter the default value for `n` unless specifically requested by
    a user.

    For example, to search for open issues about AttributeErrors with the
    label "bug" in PrefectHQ/prefect:
        - repo: prefecthq/prefect
        - query: label:bug is:open AttributeError
    """
    TOKEN_LIMIT = 1500
    headers = {"Accept": "application/vnd.github.v3+json"}

    headers["Authorization"] = f"Bearer {api_token or await _get_token()}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/search/issues",
            headers=headers,
            params={
                "q": query if "repo:" in query else f"repo:{repo} {query}",
                "order": "desc",
                "per_page": n,
            },
        )
        response.raise_for_status()

    issues_data = response.json()["items"]

    for issue in issues_data:
        if not issue["body"]:
            continue
        issue["body"] = slice_tokens(issue["body"], TOKEN_LIMIT)

    issues = [GitHubIssue(**issue) for issue in issues_data]

    summary = "\n\n".join(
        f"{issue.title} ({issue.html_url}):\n{issue.body}" for issue in issues
    )
    if not summary.strip():
        return "No issues found."
    return summary


def display_callable_signature(import_path: str) -> str:
    """
    Display the signature of any callable (function, class constructor, method) with clear visual organization.

    Works for functions, classes, methods - anything you can call with parentheses.

    Args:
        import_path: Import path to the callable (e.g., 'fastmcp.server:FastMCP' or 'json:loads')

    Returns:
        A formatted string showing the callable's signature

    Examples:
        # Get signature of a class constructor
        >>> display_callable_signature('fastmcp.server:FastMCP')

        # Get signature of a function
        >>> display_callable_signature('json:loads')

        # Get signature from a specific module
        >>> display_callable_signature('pandas.DataFrame:merge')

        # Get signature of a Prefect decorator
        >>> display_callable_signature('prefect:flow')
    """
    return display_signature(import_path)
