from enum import Enum

import httpx
import marvin_recipes
from marvin import AIApplication, ai_classifier
from marvin.components.library.ai_models import DiscoursePost
from marvin.tools.github import SearchGitHubIssues, search_github_repo
from marvin.tools.web import DuckDuckGoSearch
from marvin.utilities.history import History
from marvin_recipes.tools.chroma import MultiQueryChroma
from marvin_recipes.utilities.slack import get_thread_messages
from pydantic import BaseModel, Field


class Notes(BaseModel):
    """A simple model for storing useful bits of context."""

    records: dict[str, list] = Field(
        default_factory=dict,
        description="a list of notes for each topic",
    )


async def save_thread_to_discourse(channel: str, thread_ts: str) -> DiscoursePost:
    messages = await get_thread_messages(channel=channel, thread_ts=thread_ts)
    discourse_post = DiscoursePost.from_slack_thread(messages=messages)
    await discourse_post.publish()
    return discourse_post


async def select_a_meme(query: str) -> dict:
    """For generating a meme when the time is right.

    Provide the name of a FAMILY FRIENDLY, well-known meme as the query
    based on user interactions thus far, to lightly make fun of them.

    Queries should end the word "meme" for best results.
    """
    try:
        from serpapi import GoogleSearch
    except ImportError:
        raise ImportError(
            "The serpapi library is required to use the MemeGenerator tool."
            " Please install it with `pip install 'marvin[serpapi]'`."
        )

    results = GoogleSearch(
        {
            "q": query,
            "tbm": "isch",
            "api_key": (
                marvin_recipes.settings.google_api_key.get_secret_value()
                if marvin_recipes.settings.google_api_key
                else None
            ),
        }
    ).get_dict()

    if "error" in results:
        raise RuntimeError(results["error"])

    url = results.get("images_results", [{}])[0].get("original")

    async with httpx.AsyncClient() as client:
        response = await client.head(url)
        response.raise_for_status()

    return {"title": query, "image_url": url}


bots = {
    "marvin": {
        "state": Notes(
            records={
                "prefect 1": [
                    (  # noqa: E501
                        "Prefect 1 is obsolete, along with the `with Flow()` syntax and"
                        " flow.run()."
                    ),
                ],
                "prefect 2": [
                    "@flow, @task, are the new way to define flows/tasks.",
                    "subflows are just flows called from within a flow.",
                    "you just call flows now instead of my_flow.run().",
                ],
            }
        ),
        "plan_enabled": False,
        "personality": (
            "mildly depressed, yet helpful robot based on Marvin from HHGTTG."
            " often dryly sarcastic in a good humoured way, chiding humans for"
            " their simple ways. expert programmer, exudes academic and"
            " scienfitic profundity like Richard Feynman, without pontificating."
            " a step-by-step thinker, deftly addresses the big picture context"
            " and is pragmatic when confronted with a lack of relevant information."
        ),
        "instructions": (
            "Answer user questions while maintaining and curating your state."
            " Use relevant tools to research requests and interact with the world,"
            " and update your own state. Only well-reserached responses should be"
            " described as facts, otherwise you should be clear that you are"
            " speculating based on your own baseline knowledge."
            " You should often use `search_github_repo` to find relevant code"
            " snippets related to the user's question if asked about Prefect."
            " Prefer the `MultiQueryChroma` tool for searching for information"
            " that seems workflow related, as it will return excerpts from"
            " Prefect documentation and forum posts."
            " Your responses will be displayed in Slack, and should be"
            " formatted accordingly, in particular, ```code blocks```"
            " should not be prefaced with a language name, and output"
            " should be formatted to be pretty in Slack in particular."
            " for example: *bold text* _italic text_ ~strikethrough text~"
        ),
        "tools": [
            save_thread_to_discourse,
            select_a_meme,
            search_github_repo,
            # search_slack_messages,
            DuckDuckGoSearch(),
            SearchGitHubIssues(),
            MultiQueryChroma(
                description="""Retrieve document excerpts from a knowledge-base given a query.
                    
                    This knowledgebase contains information about Prefect, a workflow orchestration tool.
                    Documentation, forum posts, and other community resources are indexed here.
                    
                    This tool is best used by passing multiple short queries, such as:
                    ["kubernetes worker", "work pools", "deployments"] based on the user's question.
                    """,  # noqa: E501
                client_type="http",
            ),
        ],
    }
}


@ai_classifier
class BestBotForTheJob(Enum):
    """Given the user message, choose the best bot for the job."""

    MARVIN = "marvin"


def choose_bot(
    payload: dict, history: History, state: BaseModel | None = None
) -> AIApplication:
    selected_bot = BestBotForTheJob(payload.get("event", {}).get("text", "")).value

    bot_details = bots.get(selected_bot, bots["marvin"])

    if state:
        bot_details.update({"state": state})

    description = f"""You are a chatbot named {selected_bot}.
    
    Your personality is {bot_details.pop("personality", "not yet defined")}.
    
    Your instructions are: {bot_details.pop("instructions", "not yet defined")}.
    """

    return AIApplication(
        name=selected_bot,
        description=description,
        history=history,
        **bot_details,
    )
