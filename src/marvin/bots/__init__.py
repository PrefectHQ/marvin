import asyncio
import marvin
from . import fun, utilities, meta, jobs, assistants


async def install_bots():
    from marvin import Bot

    for module in [fun, meta, jobs, assistants]:
        for bot in module.__dict__.values():
            if isinstance(bot, Bot):
                await bot.save(if_exists="update")


if marvin.settings.bot_create_default_bots_on_startup:
    asyncio.run(install_bots())
