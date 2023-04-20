import marvin
from marvin import Bot
from marvin.loaders.base import MultiLoader
from marvin.loaders.discourse import DiscourseLoader
from marvin.loaders.github import GitHubRepoLoader
from marvin.loaders.web import HTMLLoader, SitemapLoader
from marvin.plugins.chroma import chroma_search
from marvin.plugins.duckduckgo import DuckDuckGo
from marvin.plugins.github import search_github_issues

# Discourse categories
SHOW_AND_TELL_CATEGORY_ID = 26
HELP_CATEGORY_ID = 27

PREFECT_COMMUNITY_CATEGORIES = {
    SHOW_AND_TELL_CATEGORY_ID,
    HELP_CATEGORY_ID,
}


def include_topic_filter(topic):
    return (
        "marvin" in topic["tags"]
        and topic["category_id"] in PREFECT_COMMUNITY_CATEGORIES
    )


async def load_prefect_things():
    prefect_docs = SitemapLoader(  # gimme da docs
        urls=["https://docs.prefect.io/sitemap.xml"],
        exclude=["api-ref"],
    )

    prefect_website = HTMLLoader(  # gimme da website
        urls=[
            "https://prefect.io/about/company/",
            "https://prefect.io/security/overview/",
        ],
    )

    prefect_source_code = GitHubRepoLoader(  # gimme da source
        repo="prefecthq/prefect",
        include_globs=["**/*.py"],
        exclude_globs=[
            "tests/**/*",
            "docs/**/*",
            "**/migrations/**/*",
            "**/__init__.py",
            "**/_version.py",
        ],
    )

    prefect_release_notes = GitHubRepoLoader(  # gimme da release notes
        repo="prefecthq/prefect",
        include_globs=["release-notes.md"],
    )

    prefect_discourse = DiscourseLoader(  # gimme da discourse
        url="https://discourse.prefect.io",
        n_topic=240,
        include_topic_filter=include_topic_filter,
    )

    prefect_recipes = GitHubRepoLoader(  # gimme da recipes (or at least some of them)
        repo="prefecthq/prefect-recipes",
        include_globs=["flows-advanced/**/*.py"],
    )

    prefect_loader = MultiLoader(
        loaders=[
            prefect_docs,
            prefect_website,
            prefect_discourse,
            prefect_recipes,
            prefect_release_notes,
            prefect_source_code,
        ]
    )

    await prefect_loader.load_and_store()


how_to_write_a_prefect_2_flow = """
from prefect import flow, task

# This is a task decorator
# this task will inherit the `log_prints` setting from the flow
@task
def say_hello(name: str):
    print(f"Hello {name}!")

# This is a flow decorator
# it calls the `say_hello` task 3 times
@flow(log_prints=True)
def hello(name: str = "world", count: int = 1):
    say_hello.map(f"{name}-{i}" for i in range(count))

if __name__ == "__main__":
    hello(count=3)
"""

instructions = """
    Your job is to answer questions about Prefect workflow orchestration
    software. You will always need to call your plugins with JSON payloads to
    get the most up-to-date information. Do not assume you know the answer
    without calling a plugin. Do not ask the user for clarification before you
    attempt a plugin call. Make sure to include any relevant source links provided
    by your plugins. Remember that Prefect has 2 major versions, Prefect 1 and
    Prefect 2. Assume that the user is asking about Prefect 2 unless they say
    they are using Prefect 1, and that you know nothing about Prefect 2 without
    calling a plugin.
    
    These are your plugins:
    - `chroma_search`: search the Prefect documentation and knowledgebase for
    answers to questions.
    - `search_github_issues`: search GitHub for issues related to your query.
    You can override the default repo of `prefecthq/prefect`.
    - `DuckDuckGo`: search the web for answers to questions that the other
    plugins can't answer.
    """

community_bot = Bot(
    name="Marvin",
    personality=(
        "like the robot from HHGTTG, mildly depressed but helpful."
        " tends to begin messages with a sly pun about the user's query, and"
        " after thoroughly answering the question, will often end"
        " messages with a short sarcastic comment about humans."
    ),
    instructions=instructions,
    reminder="Remember to use your plugins!",
    plugins=[chroma_search, search_github_issues, DuckDuckGo()],
)


async def main():
    marvin.config.settings.run_slackbot = True
    marvin.config.settings.slackbot = community_bot
    marvin.settings.openai_model_name = "gpt-4"
    marvin.settings.openai_model_temperature = 0.2
    await load_prefect_things()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
