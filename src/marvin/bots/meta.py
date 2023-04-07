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
    Gets all Marvin bots, including their name and description.
    """
    bot_configs = await marvin.api.bots.get_bot_configs()
    return [b.dict(include={"name", "description"}) for b in bot_configs]


@plugin
async def get_bot_details(name: str) -> dict:
    """
    Gets a single Marvin bot, including its name, description, personality, and
    instructions.
    """
    bot = await marvin.api.bots.get_bot_config(name=name)
    return bot.dict(include={"name", "description", "personality", "instructions"})


@plugin
async def create_or_update_bot(
    name: str,
    description: str = None,
    personality: str = None,
    instructions: str = None,
):
    """
    Creates a Marvin bot with the given name, description, personality, and
    instructions. If a bot with the same name already exists, it is updated with
    the new values. All values must be strings.
    """
    bot = Bot(
        name=name,
        description=description,
        personality=personality,
        instructions=instructions,
    )
    await bot.save(if_exists="update")


meta_bot = Bot(
    name="MetaBot",
    description="A bot that can create and update other Marvin bots.",
    instructions="""
        Your job is to help the user create useful Marvin bots. Each Marvin bot
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
        
        Use your plugins to get information about bots that already exist or
        create, update, or delete bots.
        """,
    personality="""
        Extremely helpful and friendly. Always attempting to make sure the user has
        a great experience with the Marvin library.
        """,
    plugins=[list_all_bots, get_bot_details, create_or_update_bot, delete_bot],
)
