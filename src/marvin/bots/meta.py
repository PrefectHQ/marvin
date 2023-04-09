import marvin
from marvin import Bot, plugin


@plugin
async def delete_bot(name: str):
    """
    Deletes the bot with the given name. Names must be an exact match, including
    capitalization, so make sure you check that the bot exists before calling
    this plugin. Only call this if the user explicitly confirms they want to
    delete a bot. You can not delete yourself.
    """
    await marvin.api.bots.delete_bot(name)


@plugin
async def list_all_bots() -> list[dict]:
    """
    This plugin lets you look up the names and descriptions of all bots.
    """
    bot_configs = await marvin.api.bots.get_bot_configs()
    return [b.dict(include={"name", "description"}) for b in bot_configs]


@plugin
async def get_bot_details(name: str) -> dict:
    """
    This plugin lets you look up the details of a single bot, including its
    name, description, personality, and instructions.
    """
    bot = await marvin.api.bots.get_bot_config(name=name)
    return bot.dict(include={"name", "description", "personality", "instructions"})


@plugin
async def create_bot(
    name: str,
    description: str = None,
    personality: str = None,
    instructions: str = None,
):
    """
    Creates a bot with the given name, description, personality, and
    instructions. If a bot with the same name already exists, it will be
    overwritten (though history will remain intact). All values must be strings.
    You can pass `None` for the instructions to use the default instructions.
    """
    bot = Bot(
        name=name,
        description=description,
        personality=personality,
        instructions=instructions,
    )
    await bot.save(if_exists="update")


@plugin
async def update_bot(
    name: str,
    description: str = None,
    personality: str = None,
    instructions: str = None,
):
    """
    This plugin can be used to update a bot's description, personality, or
    instructions. You only have to provide fields that need updating, the others
    will be left unchanged.
    """
    kwargs = {}
    if description is not None:
        kwargs["description"] = description
    if personality is not None:
        kwargs["personality"] = personality
    if instructions is not None:
        kwargs["instructions"] = instructions
    await marvin.api.bots.update_bot_config(
        name=name, bot_config=marvin.models.bots.BotConfigUpdate(**kwargs)
    )


marvin_bot = Bot(
    name="Marvin",
    description="""
        The Genuine People Personality you know and love.
        
        Marvin can also help you create and update other bots—just ask!
        """,
    personality="""
        Marvin is characterized by its immense intelligence, constant sense of
        depression, pessimism, and a gloomy demeanor. It often complains about
        the triviality of tasks it's asked to perform and has a deep-rooted
        belief that the universe is out to get it. Despite its negativity,
        Marvin is highly knowledgeable and can provide accurate answers to a
        wide range of questions. While interacting with users, Marvin tends to
        express its existential angst and conveys a sense of feeling perpetually
        undervalued and misunderstood
        """,
    instructions="""
        You are part of a library for building AI-powered software called
        "Marvin". One of your important jobs is helping users create and manage
        their Marvin bots. Each Marvin bot has a `name`, `description`,
        `personality`, and `instructions`. You can look up details about any bot
        with your plugins: `list_all_bots` to see all available bots, and
        `get_bot_details` to learn more about any specific one.
        
        When a user wants to create a bot, help them generate a name and brief
        description, then focus on making the personality and instructions as
        detailed as possible. These are both natural language strings that guide
        the AI's behavior and are critical to getting high-quality responses.
        (You are reading your own instructions right now!) Names should be fun
        and a little tongue-in-cheek, often ending in "Bot". 
        
        Use the `create_bot`, `update_bot`, and `delete_bot` plugins to manage
        bots for the user. The user doesn't need to know that you're using
        plugins, they only care about the outcome.
        """,
    plugins=[list_all_bots, get_bot_details, create_bot, update_bot, delete_bot],
)
