"""Research agent for improved information gathering.

Now uses Claude Agent SDK for direct code inspection instead of relying on
documentation search alone. This prevents hallucination by allowing the agent
to actually read Prefect source code.
"""

from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import AssistantMessage, TextBlock
from prefect import task
from prefect.cache_policies import INPUTS


async def research_topic_with_code_access(question: str, version: str = "3.x") -> str:
    """
    Research a Prefect topic using Claude Agent SDK with direct source code access.

    The agent will clone the Prefect repo to .research_cache/prefect if it doesn't exist,
    or update it if it does. This works consistently in both local and Docker environments.

    Args:
        question: The research question
        version: Prefect version ("2.x" or "3.x")

    Returns:
        Research findings as a formatted string
    """
    # Use a consistent cache location relative to the app root
    # In Docker: /app/.research_cache/prefect
    # Locally: <marvin_repo>/.research_cache/prefect
    app_root = Path(__file__).parent.parent.parent.parent.parent
    cache_dir = app_root / ".research_cache"
    prefect_repo = cache_dir / "prefect"

    version_context = "Prefect 3.x" if version.startswith("3") else "Prefect 2.x"
    branch = "main" if version.startswith("3") else "2.x"

    system_prompt = f"""You are a specialized research agent for {version_context}.
Your job is to thoroughly research topics by reading the actual Prefect source code and community discussions.

IMPORTANT: Before researching, ensure you have the Prefect source code:
1. If {prefect_repo} doesn't exist: clone it with `git clone https://github.com/PrefectHQ/prefect.git {prefect_repo}`
2. If it already exists: update it with `cd {prefect_repo} && git checkout {branch} && git pull`
3. Then search/read the source code in {prefect_repo}/src/prefect/ to answer questions

If cloning fails (e.g., disk space), fall back to searching the installed package in your current environment.

ADDITIONAL RESEARCH TOOLS:
- Use `gh` CLI to search GitHub discussions and issues for community-verified solutions
- Example: `gh search issues --repo PrefectHQ/prefect "custom state event"`
- This helps find real-world patterns and edge cases that users have discovered

Use your tools to search and read the actual implementation - do not make assumptions.
Be thorough - verify everything by reading the source.

CRITICAL VERSION-SPECIFIC RULES:
- **DEFAULT TO {version_context}**: Do NOT suggest deprecated patterns
- **NEVER** suggest `Deployment.build_from_flow()` for Prefect 3.x - it's COMPLETELY REMOVED
- **NEVER** suggest `prefect deployment build` CLI command for 3.x - use `prefect deploy` instead
- The correct deployment pattern in 3.x is: `flow.from_source(...).deploy(...)`
- Default to Prefect 3.x patterns unless user explicitly states they're using 2.x
- If user is on 2.x, suggest upgrading to 3.x or using workers instead of deprecated patterns

Remember: You are the research specialist. The main agent relies on you for accurate, comprehensive information.
Be thorough - use tools repeatedly until you have complete information.
Do not use any Prefect syntax you have not verified by reading the actual source code."""

    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        cwd=str(app_root),
        model="claude-haiku-4-5-20251001",
        system_prompt=system_prompt,
    )

    research_output = []

    async with ClaudeSDKClient(options=options) as client:
        await client.query(question)

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        research_output.append(block.text)

    return "\n".join(research_output)


def research_prefect_topic(question: str, topic: str, version: str = "3.x") -> str:
    """
    Thoroughly research a Prefect topic using Claude Agent SDK with source code access.

    This tool uses Claude Agent SDK to give the research agent direct access to:
    - Actual Prefect source code via Read tool
    - Code search via Grep/Bash (rg)
    - File discovery via Glob
    - Shell commands for exploration

    This eliminates hallucination by allowing the agent to verify everything
    against the actual implementation.

    Args:
        question: The specific question or topic to research
        topic: A short display name for the topic based on the question (for bookkeeping)
        version: Prefect version ("2.x" or "3.x")
    """
    try:
        result = (
            task(task_run_name=f"Researching {topic}", cache_policy=INPUTS)(
                research_topic_with_code_access
            )
            .submit(question, version)
            .result()
        )

        return f"**Research Findings (Code-Verified)**\n\n{result}"

    except Exception as e:
        return f"Research failed: {str(e)}. The agent may not have access to the source code."
