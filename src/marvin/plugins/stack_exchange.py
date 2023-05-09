import httpx
from pydantic import BaseModel, Field

import marvin
from marvin.plugins import plugin
from marvin.utilities.strings import slice_tokens


class StackExchangeQuestion(BaseModel):
    title: str
    link: str
    is_answered: bool
    view_count: int
    score: int
    creation_date: int
    question_id: int
    body_markdown: str

    body: str = Field(default_factory=str)
    tags: list[str] = Field(default_factory=list)
    owner: dict = Field(default_factory=dict)


API_BASE_URL = "https://api.stackexchange.com/2.3"


@plugin
async def search_stack_exchange(
    query: str,
    tag: str = "",
    n: int = 3,
    site: str = "stackoverflow",
    token_limit: int = 3000,
) -> str:
    """
    Use the Stack Exchange API to search for Stack Exchange questions.
    Most often used to search StackOverflow for Python questions.
    Do not alter the `tag` argument unless you're told explicitly.


    For example, to search StackOverflow for questions about reading files in Python:
        - query: How to read a file?
        - site: stackoverflow
        - tag: python
    """
    headers = {"Accept": "application/json"}

    if token := marvin.settings.stackexchange_api_key.get_secret_value():
        headers["X-API-Key"] = token

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/search",
            headers=headers,
            params={
                "site": site,
                "sort": "relevance",
                "tagged": tag,
                "intitle": query,
                "pagesize": n,
                "filter": (  # https://api.stackexchange.com/docs/create-filter
                    "!)s-rqpmcJW_bgI7R1S8n"
                ),
            },
        )
        response.raise_for_status()

    summary = ""

    for question in (StackExchangeQuestion(**q) for q in response.json()["items"]):
        question_summary = (
            f"{question.title} ({question.link}):\n{question.body} | tags"
            f" {question.tags!r}\n\n"
        )
        summary += question_summary

    if not summary.strip():
        raise ValueError("No questions found.")
    return slice_tokens(summary, token_limit)
