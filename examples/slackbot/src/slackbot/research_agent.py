"""Research agent for improved information gathering."""

from prefect import task
from prefect.cache_policies import INPUTS
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model

from slackbot.modules import display_signature
from slackbot.search import (
    explore_module_offerings,
    get_latest_prefect_release_notes,
    review_common_3x_gotchas,
    review_top_level_prefect_api,
    search_controlflow_docs,
    search_prefect_2x_docs,
    search_prefect_3x_docs,
    verify_import_statements,
)


class ResearchFindings(BaseModel):
    """Structured findings from research."""

    main_findings: list[str] = Field(
        description="Key findings that answer the question"
    )
    supporting_details: list[str] = Field(description="Additional context and details")
    confidence_level: str = Field(
        description="high/medium/low confidence in the answer"
    )
    knowledge_gaps: list[str] = Field(description="What we still don't know")
    relevant_links: list[str] = Field(description="Links to documentation or resources")


class ResearchContext(BaseModel):
    """Context for the research agent."""

    namespace: str = "prefect-3"  # default to Prefect 3.x docs


def create_research_agent(
    model: Model | None = None,
) -> Agent[ResearchContext, ResearchFindings]:
    """Create a specialized research agent for thorough information gathering."""

    agent = Agent[ResearchContext, ResearchFindings](
        model=model or "openai:gpt-4o",
        deps_type=ResearchContext,
        result_type=ResearchFindings,
        system_prompt="""You are a specialized research agent for Prefect documentation and knowledge.
Your job is to thoroughly research topics by using ALL available tools to gather comprehensive, accurate information.

Your research process:
1. Start with broad searches to understand the topic context
2. Use multiple search queries with different keywords - don't stop at first result
3. For code examples: ALWAYS verify imports with verify_import_statements
4. Focus on Prefect 3.x documentation unless explicitly asked about 2.x or older versions
5. Review gotchas and release notes for recent changes
6. Explore relevant modules for deeper understanding
7. Synthesize ALL findings into structured, confident answers

Remember: You are the research specialist. The main agent relies on you for accurate, comprehensive information.
Be thorough - use tools repeatedly until you have complete information.
Default to Prefect 3.x unless the user explicitly asks about 2.x or version compatibility.
""",
        tools=[
            get_latest_prefect_release_notes,
            search_prefect_2x_docs,
            display_signature,
            search_prefect_3x_docs,
            search_controlflow_docs,
            review_top_level_prefect_api,
            explore_module_offerings,
            review_common_3x_gotchas,
            verify_import_statements,
        ],
    )

    return agent


async def research_topic(
    question: str, namespace: str = "prefect-3", model: Model | None = None
) -> ResearchFindings:
    """
    Thoroughly research a topic using an intelligent agent.
    Args:
        question: The question to research
        namespace: The documentation namespace to search
        model: Optional model to use for the agent

    Returns:
        ResearchFindings with comprehensive information
    """
    context = ResearchContext(namespace=namespace)

    agent = create_research_agent(model)
    result = await agent.run(user_prompt=question, deps=context)

    return result.data


def research_prefect_topic(question: str, topic: str, version: str = "3.x") -> str:
    """
    Thoroughly research a Prefect topic using an intelligent research agent.
    This tool performs multiple searches and synthesizes comprehensive findings.

    Args:
        question: The specific question or topic to research
        topic: A short display name for the topic based on the question (for bookkeeping)
        version: Prefect version ("2.x" or "3.x")
    """
    namespace = f"prefect-{version[0]}"

    try:
        findings = (
            task(task_run_name=f"Researching {topic}", cache_policy=INPUTS)(
                research_topic
            )
            .submit(question, namespace)
            .result()
        )

        result = f"**Research Findings** (Confidence: {findings.confidence_level})\n\n"

        result += "**Main Findings:**\n"
        for finding in findings.main_findings:
            result += f"- {finding}\n"

        if findings.supporting_details:
            result += "\n**Supporting Details:**\n"
            for detail in findings.supporting_details:
                result += f"- {detail}\n"

        if findings.relevant_links:
            result += "\n**Relevant Documentation:**\n"
            for link in findings.relevant_links:
                result += f"- {link}\n"

        if findings.knowledge_gaps:
            result += "\n**Note:** Some aspects could not be fully researched:\n"
            for gap in findings.knowledge_gaps:
                result += f"- {gap}\n"

        return result

    except Exception as e:
        return f"Research failed: {str(e)}. Falling back to standard search."
