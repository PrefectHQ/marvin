import asyncio
import os
import subprocess
from datetime import datetime
from typing import Optional

import httpx
import turbopuffer as tpuf
from prefect import task
from prefect.blocks.system import Secret
from pydantic import BaseModel, Field, field_validator
from raggy.vectorstores.tpuf import multi_query_tpuf

import marvin
from marvin.utilities.logging import get_logger
from slackbot.modules import ModuleTreeExplorer
from slackbot.settings import settings
from slackbot.strings import slice_tokens


def verify_import_statements(import_statements: list[str]) -> str:
    """
    Verify that import statements are valid.

    Args:
        import_statements: A list of import statements to verify.

    Returns:
        A string with the results of the verification.

    Example:
        >>> verify_import_statements(["from prefect import flow"])
        "✅ from prefect import flow"

        >>> verify_import_statements(["from prefect import schleeb", "from prefect import flow"])
        "❌ from prefect import schleeb: No module named 'schleeb'\n✅ from prefect import flow"
    """
    print(f"Verifying import statements: {import_statements}")
    results: list[str] = []
    for import_statement in import_statements:
        try:
            result = subprocess.run(
                ["uv", "run", "--no-project", "python", "-c", import_statement],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                results.append(f"✅ {import_statement}")
            else:
                error_msg = result.stderr.strip().split("\n")[-1]
                results.append(f"❌ {import_statement}: {error_msg}")
        except Exception as e:
            results.append(f"❌ {import_statement}: {str(e)}")
    return "\n".join(results)


def review_top_level_prefect_api() -> str:
    """
    Review the available submodules and the top-level API of Prefect.
    """
    explorer = ModuleTreeExplorer("prefect", max_depth=0)
    explorer.explore()
    summary = explorer.get_tree_string()
    print(summary)
    return summary


def review_common_3x_gotchas() -> list[str]:
    """If needed, review common sources of confusion for Prefect 3.x users."""
    tips = [
        "from_source('https://github.com/<owner>/<repo>') has replaced the GitHub block in Prefect 3.x",
        ".map and .submit are always synchronous, even if the underlying function is asynchronous",
        "futures returned by .map can be resolved together, like integers = double.map(range(10)).result()",
        "futures must be resolved by passing them to another task, returning them or manually calling .result() or .wait()",
        "agents are replaced by workers in prefect 3.x, work pools replace the infra blocks from prefect.infrastructure",
        "prefect 3.x uses pydantic 2 and server data from prefect 2.x is not compatible with 3.x",
        "Deployment.build_from_flow() is removed in 3.x, use some_flow.from_source(...).deploy(...) instead.",
    ]
    print(tips)
    return tips


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
    summary = explorer.get_tree_string()
    print(summary)
    return summary


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


def search_controlflow_docs(queries: list[str]) -> str:
    """Searches the ControlFlow documentation for the given queries.

    ControlFlow is an agentic framework built on top of Prefect 3.x.

    It is best to use more than one, short query to get the best results.
    """
    return multi_query_tpuf(queries, namespace="controlflow", n_results=5)


def get_latest_prefect_release_notes() -> str:
    """Gets the latest Prefect release notes"""
    url = "https://api.github.com/repos/PrefectHQ/prefect/releases/latest"

    print(f"Getting latest Prefect release notes from {url}")

    with httpx.Client() as client:
        response = client.get(url)
        release_notes = response.json().get("body")
        return release_notes


async def get_token() -> str:
    try:
        from prefect.blocks.system import Secret

        return (await Secret.aload(name="github-token")).get()
    except (ImportError, ValueError) as exc:
        getattr(get_logger("marvin"), "debug_kv")(
            (
                "Prefect Secret for GitHub token not retrieved. "
                f"{exc.__class__.__name__}: {exc}"
                "red"
            ),
        )

    try:
        return getattr(marvin.settings, "github_token")
    except AttributeError:
        pass

    if token := os.environ.get("MARVIN_GITHUB_TOKEN", ""):
        return token

    raise RuntimeError("GitHub token not found")


class GitHubUser(BaseModel):
    """GitHub user."""

    login: Optional[str] = None


class GitHubComment(BaseModel):
    """GitHub comment."""

    body: str = Field(default="")
    user: GitHubUser = Field(default_factory=GitHubUser)


class GitHubLabel(BaseModel):
    """GitHub label."""

    name: str = Field(default="")


class GitHubIssue(BaseModel):
    """GitHub issue."""

    created_at: datetime = Field(...)
    html_url: str = Field(...)
    number: int = Field(...)
    title: str = Field(default="")
    body: str | None = Field(default="")
    labels: list[GitHubLabel] = Field(default_factory=GitHubLabel)
    user: GitHubUser = Field(default_factory=GitHubUser)

    @field_validator("body")
    def validate_body(cls, v: str) -> str:
        if not v:
            return ""
        return v


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
    # Load GitHub token synchronously
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
    headers = {"Accept": "application/vnd.github.v3+json"}

    headers["Authorization"] = f"Bearer {api_token or await get_token()}"

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

    # enforce 1000 token limit per body
    for issue in issues_data:
        if not issue["body"]:
            continue
        issue["body"] = slice_tokens(issue["body"], 1000)

    issues = [GitHubIssue(**issue) for issue in issues_data]

    summary = "\n\n".join(
        f"{issue.title} ({issue.html_url}):\n{issue.body}" for issue in issues
    )
    if not summary.strip():
        return "No issues found."
    return summary
