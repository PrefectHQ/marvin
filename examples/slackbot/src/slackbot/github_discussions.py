"""GitHub Discussions tools for the Slack bot."""

import json
import subprocess
from typing import Optional

from pydantic import BaseModel
from pydantic_ai import RunContext

from marvin.utilities.logging import get_logger

logger = get_logger(__name__)

DEFAULT_REPO = "prefecthq/prefect"


class Discussion(BaseModel):
    """GitHub Discussion model."""

    id: str
    number: int
    title: str
    body: str
    category: str
    created_at: str
    url: str
    author_login: str
    comments_count: int = 0


def _search_discussions_graphql(
    query: str,
    repo: str = DEFAULT_REPO,
    limit: int = 5,
) -> list[Discussion]:
    """Internal: Search GitHub discussions using GraphQL."""

    search_query = f"repo:{repo} {query}"

    graphql_query = """
    query($searchQuery: String!, $limit: Int!) {
      search(query: $searchQuery, type: DISCUSSION, first: $limit) {
        nodes {
          ... on Discussion {
            id
            number
            title
            body
            category { name }
            createdAt
            url
            author { login }
            comments { totalCount }
          }
        }
      }
    }
    """

    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={graphql_query}",
        "-f",
        f"searchQuery={search_query}",
        "-F",
        f"limit={limit}",
        "--jq",
        ".",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        discussions = []
        for node in data.get("data", {}).get("search", {}).get("nodes", []):
            if node:
                discussions.append(
                    Discussion(
                        id=node["id"],
                        number=node["number"],
                        title=node["title"],
                        body=node["body"],
                        category=node.get("category", {}).get("name", "General"),
                        created_at=node["createdAt"],
                        url=node["url"],
                        author_login=node.get("author", {}).get("login", "unknown"),
                        comments_count=node.get("comments", {}).get("totalCount", 0),
                    )
                )

        return discussions

    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.error(f"Failed to search discussions: {e}")
        return []


def _read_discussion_graphql(
    number: int,
    repo: str = DEFAULT_REPO,
) -> Optional[Discussion]:
    """Internal: Read a specific discussion."""

    owner, repo_name = repo.split("/")

    graphql_query = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        discussion(number: $number) {
          id
          number
          title
          body
          category { name }
          createdAt
          url
          author { login }
          comments { totalCount }
        }
      }
    }
    """

    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={graphql_query}",
        "-f",
        f"owner={owner}",
        "-f",
        f"repo={repo_name}",
        "-F",
        f"number={number}",
        "--jq",
        ".",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        node = data.get("data", {}).get("repository", {}).get("discussion")
        if node:
            return Discussion(
                id=node["id"],
                number=node["number"],
                title=node["title"],
                body=node["body"],
                category=node.get("category", {}).get("name", "General"),
                created_at=node["createdAt"],
                url=node["url"],
                author_login=node.get("author", {}).get("login", "unknown"),
                comments_count=node.get("comments", {}).get("totalCount", 0),
            )
        return None

    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.error(f"Failed to read discussion: {e}")
        return None


def _create_discussion_graphql(
    title: str,
    body: str,
    category: str = "General",
    repo: str = DEFAULT_REPO,
) -> Optional[Discussion]:
    """Internal: Actually create a discussion via GraphQL."""

    owner, repo_name = repo.split("/")

    # Get repository and category IDs
    query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        id
        discussionCategories(first: 20) {
          nodes { id name }
        }
      }
    }
    """

    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={query}",
        "-f",
        f"owner={owner}",
        "-f",
        f"repo={repo_name}",
        "--jq",
        ".",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        repo_data = data.get("data", {}).get("repository", {})
        repo_id = repo_data.get("id")

        # Find category ID
        category_id = None
        for cat in repo_data.get("discussionCategories", {}).get("nodes", []):
            if cat and cat.get("name") == category:
                category_id = cat["id"]
                break

        if not repo_id or not category_id:
            logger.error(f"Failed to find repo or category: {category}")
            return None

        # Create the discussion
        mutation = """
        mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
          createDiscussion(input: {
            repositoryId: $repositoryId,
            categoryId: $categoryId,
            title: $title,
            body: $body
          }) {
            discussion {
              id
              number
              title
              body
              category { name }
              createdAt
              url
              author { login }
              comments { totalCount }
            }
          }
        }
        """

        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-f",
            f"repositoryId={repo_id}",
            "-f",
            f"categoryId={category_id}",
            "-f",
            f"title={title}",
            "-f",
            f"body={body}",
            "--jq",
            ".",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        node = data.get("data", {}).get("createDiscussion", {}).get("discussion")
        if node:
            return Discussion(
                id=node["id"],
                number=node["number"],
                title=node["title"],
                body=node["body"],
                category=node.get("category", {}).get("name", category),
                created_at=node["createdAt"],
                url=node["url"],
                author_login=node.get("author", {}).get("login", "bot"),
                comments_count=0,
            )

        return None

    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.error(f"Failed to create discussion: {e}")
        return None


# Tools for the agent


def search_discussions(
    ctx: RunContext,
    query: str,
    repo: str = DEFAULT_REPO,
    limit: int = 5,
) -> str:
    """
    Search GitHub discussions for relevant content.

    Args:
        query: Search query
        repo: Repository (default: prefecthq/prefect)
        limit: Max results (default: 5)

    Returns:
        Formatted search results
    """
    discussions = _search_discussions_graphql(query, repo, limit)

    if not discussions:
        return f"No discussions found for query: {query}"

    results = [f"Found {len(discussions)} discussions:\n"]
    for d in discussions:
        results.append(f"#{d.number}: {d.title}")
        results.append(f"  URL: {d.url}")
        results.append(f"  Category: {d.category} | Comments: {d.comments_count}")
        results.append("")

    return "\n".join(results)


def read_discussion(
    ctx: RunContext,
    number: int,
    repo: str = DEFAULT_REPO,
) -> str:
    """
    Read a specific GitHub discussion.

    Args:
        number: Discussion number
        repo: Repository (default: prefecthq/prefect)

    Returns:
        Discussion content
    """
    discussion = _read_discussion_graphql(number, repo)

    if not discussion:
        return f"Discussion #{number} not found"

    return f"""Discussion #{discussion.number}: {discussion.title}
Category: {discussion.category}
Author: {discussion.author_login}
URL: {discussion.url}
Comments: {discussion.comments_count}

{discussion.body}"""


def create_discussion_from_slack(
    ctx: RunContext,
    title: str,
    body: str,
    category: str = "General",
    repo: str = DEFAULT_REPO,
    slack_thread_url: Optional[str] = None,
    require_approval: bool = True,
) -> str:
    """
    Create a GitHub discussion from valuable Slack content.

    This tool should be used VERY SPARINGLY and only for truly valuable content.
    By default, it requires approval (returns a proposal instead of creating).

    Args:
        title: Discussion title
        body: Discussion body
        category: Category (default: General)
        repo: Repository (default: prefecthq/prefect)
        slack_thread_url: Optional Slack thread URL
        require_approval: If True, returns proposal. If False, creates immediately.

    Returns:
        Proposal message or creation result
    """
    if slack_thread_url:
        body = f"{body}\n\n---\n*Created from [Slack thread]({slack_thread_url})*"

    if require_approval:
        # Return a proposal for the user to review
        return f"""📝 **Proposed GitHub Discussion**

**Repository:** {repo}
**Category:** {category}
**Title:** {title}

**Body:**
{body}

---
*To create this discussion, please confirm. You can also suggest edits.*

Note: This would create discussion #{_get_next_discussion_number(repo)} in {repo}."""

    # Actually create the discussion
    discussion = _create_discussion_graphql(title, body, category, repo)

    if discussion:
        return f"✅ Created discussion #{discussion.number}: {discussion.title}\nURL: {discussion.url}"
    else:
        return "❌ Failed to create discussion. Check GitHub permissions and category."


def _get_next_discussion_number(repo: str) -> str:
    """Estimate the next discussion number (for display only)."""
    # This is just for display purposes
    discussions = _search_discussions_graphql("", repo, 1)
    if discussions:
        return str(discussions[0].number + 1)
    return "N"
