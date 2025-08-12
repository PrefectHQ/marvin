"""Discussion tools for the Slack bot agent."""

from typing import Optional

from pydantic_ai import RunContext

from marvin.utilities.logging import get_logger
from slackbot.github_discussions import (
    create_github_discussion,
    read_github_discussion,
    search_github_discussions,
)

logger = get_logger(__name__)


def search_discussions(
    ctx: RunContext,
    query: str,
    repo: str = "prefecthq/marvin",
    limit: int = 5,
    category: Optional[str] = None,
) -> str:
    """
    Search GitHub discussions for relevant content.

    This tool searches through existing GitHub discussions to find relevant information
    before creating new discussions. It helps avoid duplicates and find related content.

    Args:
        query: Semantic search query for discussions
        repo: Repository in format "owner/repo" (default: "prefecthq/marvin")
        limit: Maximum number of results (default: 5)
        category: Optional category filter

    Returns:
        Formatted string with search results
    """
    results = search_github_discussions(query, repo, limit, category)

    if not results.discussions:
        return f"No discussions found matching query: {query}"

    output = [f"Found {results.total_count} discussions matching '{query}':\n"]

    for disc in results.discussions:
        output.append(f"#{disc.number}: {disc.title}")
        output.append(f"  Category: {disc.category}")
        output.append(f"  Author: {disc.author_login}")
        output.append(f"  Created: {disc.created_at}")
        output.append(f"  URL: {disc.url}")

        # Show first 200 chars of body
        body_preview = disc.body[:200] + "..." if len(disc.body) > 200 else disc.body
        output.append(f"  Preview: {body_preview}")

        if disc.answer_chosen_at:
            output.append(f"  ✓ Answered by {disc.answer_chosen_by}")

        output.append("")  # Blank line between results

    return "\n".join(output)


def read_discussion(
    ctx: RunContext,
    discussion_number: int,
    repo: str = "prefecthq/marvin",
    include_comments: bool = False,
) -> str:
    """
    Read a specific GitHub discussion by number.

    This tool retrieves the full content of a discussion, optionally including comments.
    Use this to get complete information about a discussion before deciding whether
    to create a new one or add to an existing one.

    Args:
        discussion_number: The discussion number to read
        repo: Repository in format "owner/repo" (default: "prefecthq/marvin")
        include_comments: Whether to include comments (default: False)

    Returns:
        Formatted string with discussion content
    """
    result = read_github_discussion(discussion_number, repo, include_comments)

    if not result:
        return f"Discussion #{discussion_number} not found in {repo}"

    discussion, comments = result

    output = [
        f"Discussion #{discussion.number}: {discussion.title}",
        f"Category: {discussion.category}",
        f"Author: {discussion.author_login}",
        f"Created: {discussion.created_at}",
        f"URL: {discussion.url}",
        "",
        "Body:",
        discussion.body,
        "",
    ]

    if discussion.answer_chosen_at:
        output.append(
            f"✓ Answered by {discussion.answer_chosen_by} at {discussion.answer_chosen_at}"
        )
        output.append("")

    if include_comments and comments:
        output.append(f"Comments ({len(comments)}):")
        output.append("")

        for comment in comments:
            output.append(f"Comment by {comment.author_login} at {comment.created_at}:")
            output.append(comment.body)
            output.append("")

    return "\n".join(output)


def propose_discussion_creation(
    ctx: RunContext,
    title: str,
    body: str,
    category: str = "General",
    repo: str = "prefecthq/marvin",
    slack_thread_url: Optional[str] = None,
) -> str:
    """
    Propose creating a new GitHub discussion (requires user approval).

    This tool prepares a GitHub discussion for creation but DOES NOT create it immediately.
    It will return a proposal that requires explicit user approval before the discussion
    is actually created. Use this after searching for existing discussions and determining
    that a new one is needed.

    The discussion body should include relevant context from the Slack conversation
    and be formatted in a way that's useful for future reference.

    Args:
        title: Discussion title (should be clear and searchable)
        body: Discussion body (include context, problem, solution if applicable)
        category: Discussion category (e.g., "General", "Q&A", "Ideas", "Show and Tell")
        repo: Repository in format "owner/repo" (default: "prefecthq/marvin")
        slack_thread_url: Optional URL to the original Slack thread

    Returns:
        Proposal message indicating what would be created
    """
    # Format the body with Slack thread reference if provided
    if slack_thread_url:
        formatted_body = f"{body}\n\n---\n*This discussion was created from a [Slack thread]({slack_thread_url})*"
    else:
        formatted_body = body

    # Log the proposal
    logger.info(f"Discussion creation proposed: {title} in {repo}/{category}")

    proposal = f"""
📝 **Proposed GitHub Discussion**

**Repository:** {repo}
**Category:** {category}
**Title:** {title}

**Body:**
{formatted_body}

---
*To create this discussion, please respond with approval. You can also suggest edits before creation.*

Note: Before approving, please verify:
1. No similar discussion already exists
2. The content is valuable for future reference
3. The category is appropriate
4. Sensitive information is not included
"""

    # Store the proposal in context for later execution if approved
    if hasattr(ctx, "state") and ctx.state:
        ctx.state["pending_discussion"] = {
            "title": title,
            "body": formatted_body,
            "category": category,
            "repo": repo,
        }

    return proposal


def execute_discussion_creation(
    ctx: RunContext,
    approved: bool = False,
) -> str:
    """
    Execute the creation of a previously proposed GitHub discussion.

    This tool should only be called after propose_discussion_creation and
    after receiving explicit user approval.

    Args:
        approved: Whether the user has approved the creation

    Returns:
        Result message indicating success or cancellation
    """
    if not approved:
        return "Discussion creation cancelled."

    # Retrieve the pending discussion from context
    if (
        not hasattr(ctx, "state")
        or not ctx.state
        or "pending_discussion" not in ctx.state
    ):
        return "No pending discussion found. Please propose a discussion first."

    pending = ctx.state["pending_discussion"]

    # Create the discussion (approval check is disabled since we have explicit approval)
    discussion = create_github_discussion(
        title=pending["title"],
        body=pending["body"],
        category=pending["category"],
        repo=pending["repo"],
        require_approval=False,  # We have explicit approval
    )

    if discussion:
        # Clear the pending discussion
        del ctx.state["pending_discussion"]

        return f"""
✅ Discussion created successfully!

**Discussion #{discussion.number}:** {discussion.title}
**URL:** {discussion.url}
**Category:** {discussion.category}

The discussion has been created and is now available for the community.
"""
    else:
        return """
❌ Failed to create discussion.

Please check:
1. GitHub authentication is configured
2. The repository exists and you have write access
3. The category exists in the repository
4. Network connectivity to GitHub

You may need to create the discussion manually.
"""
