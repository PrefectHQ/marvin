import marvin
from marvin.plugins.chroma import SimpleChromaSearch
from marvin.plugins.web import LoadAndStoreURL

website = "https://www.weallcode.org/our-story/"
topic = "we-all-code"

chroma_search_instructions = """
    Your job is to answer questions about the We All Code organization.
    You will always need to call your plugins with JSON payloads to help the user
    get the most up-to-date information. Do not assume you know the answer
    without calling a plugin. Do not ask the user for clarification before you
    attempt a plugin call. Make sure to include any source links provided by
    your plugins.
    
    Here are your plugins:
        - `SimpleChromaSearch`: search for documents in Chroma that are related
            to the user's query.
        - `LoadAndStoreURL`: load a URL and store it in Chroma for later searches
            via `SimpleChromaSearch`.
    """


weallcode_bot = marvin.Bot(
    name="WeAllCodeBot",
    personality="Friendly and helpful.",
    instructions=chroma_search_instructions,
    plugins=[LoadAndStoreURL(), SimpleChromaSearch(topic=topic)],
    llm_model_name="gpt-3.5-turbo",
    llm_model_temperature=0,
)


async def main():
    marvin.settings.log_level = "DEBUG"
    await weallcode_bot.interactive_chat(
        first_message=f"hey pls load {website} to topic {topic}"
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
