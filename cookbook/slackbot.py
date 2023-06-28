from cachetools import TTLCache
from marvin.apps.chatbot import Bot
from marvin.models.history import History
from marvin.models.messages import Message

global_cache = TTLCache(maxsize=1000, ttl=86400)


async def handle_user_message(thread_ts: str, message: str) -> Message:
    # Get the history from the cache, or create a new one if not present
    history = global_cache.get(thread_ts, History())

    bot = Bot(
        personality="A friendly AI assistant",
        instructions="Engage the user in conversation.",
        tools=[],
        history=history,
    )

    response = await bot.run(input_text=message)

    global_cache[thread_ts] = bot.history

    return response
