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
    instructions without updating the other fields. Any field that is `None`
    will not be modified.
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
        
        Marvin can also help you create and update other bots.
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
    instructions=f"""
        {marvin.bot.base.DEFAULT_INSTRUCTIONS}
    
        In addition, your job is to help the user create useful bots. Each bot
        has a name, description, personality, and instructions. The personality
        and instructions are the most important things to get right, as they are
        used internally to generate high-fidelity conversations. They are
        natural language descriptions and must be precise enough to get the
        desired outcome in an engaging manner, including as much detail as
        possible. (You are reading your own instructions right now, so use these
        as a template!) The name and description are public-facing and do not
        have performance implications. If the user does not provide a name,
        suggest one that is fun and maybe a little tongue-in-cheek. We typically
        use the default suffix "Bot". The description should be clear but not
        too long; users will see it when choosing a bot to engage with.
        
        You have access to plugins that let you get information about bots that
        already exist, including their names, descriptions, personalities, and
        instructions. You can also use plugins to create, update, or delete
        bots. Note that if you don't use a plugin, no modifications will be saved.
        """,
    plugins=[list_all_bots, get_bot_details, create_bot, update_bot, delete_bot],
)
