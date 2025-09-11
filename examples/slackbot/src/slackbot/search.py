import asyncio
import subprocess

import httpx
from prefect import task
from pretty_mod import display_signature
from raggy.vectorstores.tpuf import multi_query_tpuf

from slackbot.github import format_issues_summary, search_issues


def explore_module_offerings(
    module_path: str, max_depth: int = 1, with_packages: list[str] | None = None
) -> str:
    """
    Explore and return the public API tree of a specific module and its submodules as a string.

    This is the primary tool for understanding what's available in Python modules.
    Use different max_depth values based on how deep you want to explore.

    Args:
        module_path: String representing the module path (e.g., 'prefect.runtime', 'json', 'pandas')
        max_depth: Maximum depth to explore in the module tree (default: 1)
        with_packages: Optional list of packages to install for the exploration (e.g., ['prefect[aws]', 'boto3'])

    Returns:
        str: A formatted string representation of the module tree

    Common Examples:
        # Get top-level Prefect API overview
        >>> explore_module_offerings('prefect', max_depth=0)

        # Explore Prefect's runtime module in detail
        >>> explore_module_offerings('prefect.runtime', max_depth=2)

        # Explore AWS integration modules
        >>> explore_module_offerings('prefect_aws.ecs', max_depth=1, with_packages=['prefect[aws]'])

        # See what's in a specific submodule
        >>> explore_module_offerings('prefect.artifacts', max_depth=0)
    """
    # Build the command
    cmd = ["uvx"]
    if with_packages:
        for package in with_packages:
            cmd.extend(["--with", package])
    cmd.extend(["pretty-mod", "tree"])

    cmd.extend([module_path, "--depth", str(max_depth)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        # Check if it failed due to missing module
        if result.returncode != 0:
            error_output = result.stderr or result.stdout
            if "missing dependency" in error_output.lower():
                # Extract the missing module name if possible
                if "'" in error_output:
                    missing = error_output.split("'")[1]
                    return f"Module '{missing}' not found. Try specifying with_packages parameter with the required package (e.g., 'prefect[aws]', 'prefect-aws', or any PyPI package)."
            return f"Error exploring module: {error_output}"

        # Return the formatted tree output
        return result.stdout if result.stdout else "No output from module exploration"

    except subprocess.TimeoutExpired:
        return "Module exploration timed out after 30 seconds"
    except Exception as e:
        return f"Error running pretty-mod: {str(e)}"


def review_common_3x_gotchas() -> list[str]:
    """If needed, review common sources of confusion for Prefect 3.x users."""
    tips = [
        "CRITICAL: Deployment.build_from_flow() DOES NOT EXIST IN PREFECT 3.x - it has been COMPLETELY REMOVED. Never suggest it for 3.x users.",
        "CORRECT 3.x deployment pattern: flow.from_source('https://github.com/owner/repo').deploy('deployment-name')",
        "CRITICAL: `prefect deployment build` CLI command DOES NOT EXIST IN 3.x - use `prefect deploy` instead",
        "from_source('https://github.com/<owner>/<repo>') has replaced the GitHub block in Prefect 3.x",
        ".map and .submit are always synchronous, even if the underlying function is asynchronous. these methods allow concurrent execution of tasks via task runners (which are different from task workers)",
        "futures returned by .map can be resolved together, like integers = double.map(range(10)).result()",
        "futures must be resolved by passing them to another task, returning them or manually calling .result() or .wait()",
        "agents are replaced by workers in prefect 3.x, work pools replace the infra blocks from prefect.infrastructure",
        "the `prefect.infrastructure` module IS COMPLETELY REMOVED IN 3.x, see work pools instead",
        "prefect 3.x uses pydantic 2 and server data from prefect 2.x is not compatible with 3.x",
        "Workers (f.k.a. agents) poll for scheduled runs, whereas task workers are websocket clients that executed backgrounded task runs",
        "To avoid interactivity in the Prefect CLI, use the TOP LEVEL --no-prompt flag, e.g. `prefect --no-prompt deploy ...`",
        "If user is on 2.x and asking about deployments, recommend upgrading to 3.x or using workers instead of build_from_flow",
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
    return asyncio.run(_read_github_issues_async(query, repo, n))


async def _read_github_issues_async(query: str, repo: str, n: int) -> str:
    """Async helper for reading GitHub issues."""
    issues = await search_issues(query, repo=repo, n=n)
    return await format_issues_summary(issues)


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


def check_cli_command(command: str, args: list[str] | None = None) -> str:
    """
    Run a CLI command to verify its behavior or check help documentation.

    This tool is specifically designed to help verify Prefect CLI commands before suggesting them to users.
    Use this to check if a command exists, what its options are, or to verify the correct syntax.

    IMPORTANT USAGE GUIDELINES:
    - Use this tool BEFORE suggesting any CLI command to a user
    - Always check with --help first to verify command structure
    - Common commands to verify: prefect deploy, prefect work-pool, prefect worker, etc.
    - This helps prevent suggesting non-existent or incorrectly formatted commands
    - For commands that require optional dependencies, use `uv run --with prefect[<extra>]` syntax
      Examples: `uv run --with prefect[aws]`, `uv run --with prefect[docker]`, `uv run --with prefect[kubernetes]`

    Args:
        command: The base command to run (e.g., "prefect", "prefect deploy", "uv run --with prefect[docker] prefect")
        args: Additional arguments to pass (e.g., ["--help"], ["work-pool", "create", "--help"])

    Returns:
        The output of the command or an error message if it fails

    Examples:
        # Check if a command exists and see its options
        >>> check_cli_command("prefect deploy", ["--help"])

        # Verify work pool commands
        >>> check_cli_command("prefect work-pool", ["--help"])

        # Check specific subcommand help
        >>> check_cli_command("prefect", ["worker", "start", "--help"])

        # Check commands that need optional extras
        >>> check_cli_command("uv run --with prefect[docker]", ["prefect", "work-pool", "create", "--help"])
    """
    if args is None:
        args = []

    # Construct the full command
    full_command = command.split() + args

    try:
        # Run the command with a timeout
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,  # Don't raise on non-zero exit codes
        )

        # Combine stdout and stderr for complete output
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"

        if not output.strip():
            output = f"Command ran successfully with exit code {result.returncode} but produced no output"

        return output[:2000]  # Limit output length to prevent huge responses

    except subprocess.TimeoutExpired:
        return "Command timed out after 10 seconds"
    except FileNotFoundError:
        return f"Command '{full_command[0]}' not found. Make sure it's installed and in PATH."
    except Exception as e:
        return f"Error running command: {str(e)}"


def get_support_resources() -> dict[str, str]:
    """
    Get available support resources and contact information for Prefect users.

    Use this tool when users ask about getting help, support, or contacting Prefect.
    Prioritizes community resources for open source users, with email support for customers.

    Returns:
        dict: Available support resources prioritized by user type
    """
    return {
        "github_discussions": "https://github.com/PrefectHQ/prefect/discussions",
        "github_issues": "https://github.com/PrefectHQ/prefect/issues",
        "customer_support_email": "help@prefect.io (for existing customers only)",
    }
