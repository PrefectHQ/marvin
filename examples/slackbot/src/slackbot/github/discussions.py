"""GitHub Discussions operations."""

from pydantic_ai import RunContext

from ..types import UserContext
from .client import GitHubClient
from .models import DiscussionCategory, GitHubDiscussion

# Discussion category preferences (in order of preference)
PREFERRED_CATEGORIES = ["general", "q&a", "help", "support", "discussion"]


async def search_discussions(
    query: str,
    repo: str = "prefecthq/prefect",
    n: int = 5,
    client: GitHubClient | None = None,
) -> list[GitHubDiscussion]:
    """
    Search for GitHub discussions in a repository using GraphQL.

    Args:
        query: Search query string
        repo: Repository in format 'owner/repo'
        n: Number of discussions to return
        client: Optional GitHub client (will create one if not provided)

    Returns:
        List of GitHub discussions
    """
    should_close = client is None
    if client is None:
        client = GitHubClient()

    try:
        if should_close:
            await client.__aenter__()

        # Use GraphQL search to find discussions
        graphql_query = """
        query($searchQuery: String!, $first: Int!) {
            search(query: $searchQuery, type: DISCUSSION, first: $first) {
                nodes {
                    ... on Discussion {
                        id
                        number
                        title
                        body
                        url
                        createdAt
                        category {
                            id
                            name
                            emoji
                        }
                        author {
                            login
                            avatarUrl
                        }
                    }
                }
            }
        }
        """

        # Build search query string
        search_query = f"repo:{repo} {query}"

        data = await client.graphql(
            graphql_query, {"searchQuery": search_query, "first": n}
        )

        discussions_data = data.get("search", {}).get("nodes", [])

        discussions = []
        for disc_data in discussions_data:
            from .models import GitHubUser

            author_data = disc_data.get("author", {})
            author = GitHubUser(
                login=author_data.get("login"), avatar_url=author_data.get("avatarUrl")
            )

            discussion = GitHubDiscussion(
                id=disc_data["id"],
                number=disc_data["number"],
                title=disc_data["title"],
                body=disc_data.get("body", "")[:1000],  # Limit body length
                html_url=disc_data["url"],
                created_at=disc_data["createdAt"],
                category=disc_data.get("category", {}),
                author=author,
            )
            discussions.append(discussion)

        return discussions

    finally:
        if should_close:
            await client.__aexit__(None, None, None)


async def get_discussion_categories(
    repo: str = "prefecthq/prefect", client: GitHubClient | None = None
) -> list[DiscussionCategory]:
    """
    Get available discussion categories for a repository.

    Args:
        repo: Repository in format 'owner/repo'
        client: Optional GitHub client (will create one if not provided)

    Returns:
        List of discussion categories
    """
    should_close = client is None
    if client is None:
        client = GitHubClient()

    try:
        if should_close:
            await client.__aenter__()

        owner, name = repo.split("/")

        query = """
        query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                discussionCategories(first: 20) {
                    nodes {
                        id
                        name
                        emoji
                        description
                        isAnswerable
                    }
                }
            }
        }
        """

        data = await client.graphql(query, {"owner": owner, "name": name})
        categories_data = data["repository"]["discussionCategories"]["nodes"]

        return [
            DiscussionCategory(
                id=cat["id"],
                name=cat["name"],
                emoji=cat.get("emoji", ""),
                description=cat.get("description", ""),
                is_answerable=cat.get("isAnswerable", False),
            )
            for cat in categories_data
        ]

    finally:
        if should_close:
            await client.__aexit__(None, None, None)


async def create_discussion(
    title: str,
    body: str,
    category_id: str,
    repo: str = "prefecthq/prefect",
    client: GitHubClient | None = None,
) -> str:
    """
    Create a new GitHub discussion.

    Args:
        title: Discussion title
        body: Discussion body content
        category_id: ID of the discussion category
        repo: Repository in format 'owner/repo'
        client: Optional GitHub client (will create one if not provided)

    Returns:
        URL of the created discussion
    """
    should_close = client is None
    if client is None:
        client = GitHubClient()

    try:
        if should_close:
            await client.__aenter__()

        owner, name = repo.split("/")

        # First get repository ID
        repo_query = """
        query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                id
            }
        }
        """

        repo_data = await client.graphql(repo_query, {"owner": owner, "name": name})
        repository_id = repo_data["repository"]["id"]

        # Create the discussion
        create_mutation = """
        mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
            createDiscussion(input: {
                repositoryId: $repositoryId,
                categoryId: $categoryId,
                title: $title,
                body: $body
            }) {
                discussion {
                    url
                    number
                }
            }
        }
        """

        data = await client.graphql(
            create_mutation,
            {
                "repositoryId": repository_id,
                "categoryId": category_id,
                "title": title,
                "body": body,
            },
        )

        discussion_url = data["createDiscussion"]["discussion"]["url"]
        discussion_number = data["createDiscussion"]["discussion"]["number"]

        return f"Created discussion #{discussion_number}: {discussion_url}"

    finally:
        if should_close:
            await client.__aexit__(None, None, None)


async def create_discussion_from_thread(
    ctx: RunContext[UserContext],
    title: str,
    summary: str,
    repo: str = "prefecthq/prefect",
) -> str:
    """
    Create a GitHub discussion that synthesizes a Slack thread conversation.

    This should be used SPARINGLY and only when:
    1. The thread contains valuable insights or solutions
    2. No existing discussion covers the same topic
    3. The conversation would benefit the broader community

    Args:
        ctx: User context from the agent
        title: Clear, descriptive title for the discussion
        summary: Comprehensive summary of the thread conversation
        repo: Repository to create discussion in

    Returns:
        Message about the created discussion
    """
    async with GitHubClient() as client:
        # Get available categories and choose the most appropriate one
        categories = await get_discussion_categories(repo=repo, client=client)

        # Default to preferred category if available
        category_id = None
        for cat in categories:
            if cat.name.lower() in PREFERRED_CATEGORIES:
                category_id = cat.id
                break

        if not category_id and categories:
            # Fallback to first available category
            category_id = categories[0].id

        if not category_id:
            return "Error: No discussion categories found in repository"

        # Add metadata to the discussion body
        thread_link = f"https://{ctx.deps['workspace_name']}.slack.com/archives/{ctx.deps['channel_id']}/p{ctx.deps['thread_ts'].replace('.', '')}"

        discussion_body = f"""This discussion was created from a Slack thread conversation.

**Original Thread:** {thread_link}

---

{summary}

---

*This discussion was automatically created by the Marvin bot to preserve valuable community insights.*
"""

        try:
            result = await create_discussion(
                title=title,
                body=discussion_body,
                category_id=category_id,
                repo=repo,
                client=client,
            )
            return f"Successfully {result}"

        except Exception as e:
            return f"Error creating discussion: {str(e)}"


async def format_discussions_summary(discussions: list[GitHubDiscussion]) -> str:
    """Format discussions into a readable summary."""
    if not discussions:
        return "No discussions found."

    return "\n\n".join(
        f"**{disc.title}** (#{disc.number}) - {disc.html_url}\n"
        f"Category: {disc.category.get('name', 'Unknown')}\n"
        f"Author: {disc.author.login or 'Unknown'}\n"
        f"Created: {disc.created_at.strftime('%Y-%m-%d')}\n"
        f"Body: {disc.body[:500]}{'...' if len(disc.body) > 500 else ''}"
        for disc in discussions
    )
