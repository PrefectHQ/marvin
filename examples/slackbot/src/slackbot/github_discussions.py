"""GitHub Discussions integration for Slack bot."""

import json
import subprocess
from typing import Optional

from pydantic import BaseModel

from marvin.utilities.logging import get_logger

logger = get_logger(__name__)


class Discussion(BaseModel):
    """GitHub Discussion model."""

    id: str
    number: int
    title: str
    body: str
    category: str
    created_at: str
    updated_at: str
    author_login: str
    url: str
    answer_chosen_at: Optional[str] = None
    answer_chosen_by: Optional[str] = None
    comments_count: int = 0


class DiscussionComment(BaseModel):
    """GitHub Discussion comment model."""

    id: str
    body: str
    author_login: str
    created_at: str


class DiscussionSearchResult(BaseModel):
    """Result from searching GitHub discussions."""

    discussions: list[Discussion]
    total_count: int
    query: str


def search_github_discussions(
    query: str,
    repo: str = "prefecthq/marvin",
    limit: int = 5,
    category: Optional[str] = None,
) -> DiscussionSearchResult:
    """
    Search GitHub discussions using semantic search.

    Args:
        query: Search query for discussions
        repo: Repository in format "owner/repo"
        limit: Maximum number of results to return
        category: Optional category filter

    Returns:
        DiscussionSearchResult with matching discussions
    """
    owner, repo_name = repo.split("/")

    # Build the search query string for GitHub search
    search_query = f"repo:{repo} {query}"
    if category:
        search_query += f" category:{category}"

    # Build the GraphQL query for searching discussions
    graphql_query = """
    query($searchQuery: String!, $limit: Int!) {
      search(query: $searchQuery, type: DISCUSSION, first: $limit) {
        discussionCount
        nodes {
          ... on Discussion {
            id
            number
            title
            body
            category {
              name
            }
            createdAt
            updatedAt
            author {
              login
            }
            url
            answerChosenAt
            answerChosenBy {
              login
            }
            comments {
              totalCount
            }
          }
        }
      }
    }
    """

    variables = {
        "searchQuery": search_query,
        "limit": limit,
    }

    # Execute the GraphQL query using gh CLI
    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={graphql_query}",
        "--jq",
        ".",
    ]

    # Add variables (skip "query" since it's already in the GraphQL query)
    for key, value in variables.items():
        if isinstance(value, int):
            cmd.extend(["-F", f"{key}={value}"])
        else:
            cmd.extend(["-f", f"{key}={value}"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        discussions = []
        nodes = data.get("data", {}).get("search", {}).get("nodes", [])

        for node in nodes:
            if node:  # Skip null nodes
                discussions.append(
                    Discussion(
                        id=node["id"],
                        number=node["number"],
                        title=node["title"],
                        body=node["body"],
                        category=node["category"]["name"]
                        if node.get("category")
                        else "Uncategorized",
                        created_at=node["createdAt"],
                        updated_at=node["updatedAt"],
                        author_login=node["author"]["login"]
                        if node.get("author")
                        else "unknown",
                        url=node["url"],
                        answer_chosen_at=node.get("answerChosenAt"),
                        answer_chosen_by=node["answerChosenBy"]["login"]
                        if node.get("answerChosenBy")
                        else None,
                        comments_count=node["comments"]["totalCount"]
                        if node.get("comments")
                        else 0,
                    )
                )

        total_count = data.get("data", {}).get("search", {}).get("discussionCount", 0)

        return DiscussionSearchResult(
            discussions=discussions,
            total_count=total_count,
            query=query,
        )

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to search discussions: {e.stderr}")
        return DiscussionSearchResult(discussions=[], total_count=0, query=query)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GitHub API response: {e}")
        return DiscussionSearchResult(discussions=[], total_count=0, query=query)


def read_github_discussion(
    discussion_number: int,
    repo: str = "prefecthq/marvin",
    include_comments: bool = False,
) -> Optional[tuple[Discussion, list[DiscussionComment]]]:
    """
    Read a specific GitHub discussion by number.

    Args:
        discussion_number: The discussion number
        repo: Repository in format "owner/repo"
        include_comments: Whether to include comments

    Returns:
        Tuple of (Discussion, list[DiscussionComment]) or None if not found
    """
    owner, repo_name = repo.split("/")

    # Build the GraphQL query
    graphql_query = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        discussion(number: $number) {
          id
          number
          title
          body
          category {
            name
          }
          createdAt
          updatedAt
          author {
            login
          }
          url
          answerChosenAt
          answerChosenBy {
            login
          }
          comments(first: 50) {
            totalCount
            nodes {
              id
              body
              author {
                login
              }
              createdAt
            }
          }
        }
      }
    }
    """

    variables = {
        "owner": owner,
        "repo": repo_name,
        "number": discussion_number,
    }

    # Execute the GraphQL query
    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={graphql_query}",
        "--jq",
        ".",
    ]

    for key, value in variables.items():
        if isinstance(value, int):
            cmd.extend(["-F", f"{key}={value}"])
        else:
            cmd.extend(["-f", f"{key}={value}"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        node = data.get("data", {}).get("repository", {}).get("discussion")
        if not node:
            return None

        discussion = Discussion(
            id=node["id"],
            number=node["number"],
            title=node["title"],
            body=node["body"],
            category=node["category"]["name"]
            if node.get("category")
            else "Uncategorized",
            created_at=node["createdAt"],
            updated_at=node["updatedAt"],
            author_login=node["author"]["login"] if node.get("author") else "unknown",
            url=node["url"],
            answer_chosen_at=node.get("answerChosenAt"),
            answer_chosen_by=node["answerChosenBy"]["login"]
            if node.get("answerChosenBy")
            else None,
            comments_count=node["comments"]["totalCount"]
            if node.get("comments")
            else 0,
        )

        comments = []
        if include_comments and node.get("comments"):
            for comment_node in node["comments"].get("nodes", []):
                if comment_node:
                    comments.append(
                        DiscussionComment(
                            id=comment_node["id"],
                            body=comment_node["body"],
                            author_login=comment_node["author"]["login"]
                            if comment_node.get("author")
                            else "unknown",
                            created_at=comment_node["createdAt"],
                        )
                    )

        return discussion, comments

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to read discussion: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GitHub API response: {e}")
        return None


def create_github_discussion(
    title: str,
    body: str,
    category: str,
    repo: str = "prefecthq/marvin",
    require_approval: bool = True,
) -> Optional[Discussion]:
    """
    Create a new GitHub discussion.

    Args:
        title: Discussion title
        body: Discussion body content
        category: Discussion category name
        repo: Repository in format "owner/repo"
        require_approval: Whether to require user approval before creating

    Returns:
        Created Discussion or None if creation failed or was cancelled
    """
    if require_approval:
        # This would be called in the context where user approval can be requested
        logger.info(f"Would create discussion: {title} in {repo}/{category}")
        return None

    owner, repo_name = repo.split("/")

    # First, get the category ID
    category_query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        discussionCategories(first: 20) {
          nodes {
            id
            name
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
        f"query={category_query}",
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

        categories = (
            data.get("data", {})
            .get("repository", {})
            .get("discussionCategories", {})
            .get("nodes", [])
        )
        category_id = None

        for cat in categories:
            if cat and cat.get("name") == category:
                category_id = cat["id"]
                break

        if not category_id:
            logger.error(f"Category '{category}' not found in {repo}")
            return None

        # Now create the discussion
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
              category {
                name
              }
              createdAt
              updatedAt
              author {
                login
              }
              url
              comments {
                totalCount
              }
            }
          }
        }
        """

        # Get repository ID
        repo_query = """
        query($owner: String!, $repo: String!) {
          repository(owner: $owner, name: $repo) {
            id
          }
        }
        """

        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={repo_query}",
            "-f",
            f"owner={owner}",
            "-f",
            f"repo={repo_name}",
            "--jq",
            ".data.repository.id",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        repository_id = result.stdout.strip().strip('"')

        # Create the discussion
        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-f",
            f"repositoryId={repository_id}",
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
                category=node["category"]["name"] if node.get("category") else category,
                created_at=node["createdAt"],
                updated_at=node["updatedAt"],
                author_login=node["author"]["login"]
                if node.get("author")
                else "unknown",
                url=node["url"],
                answer_chosen_at=None,
                answer_chosen_by=None,
                comments_count=0,
            )

        return None

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create discussion: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GitHub API response: {e}")
        return None
