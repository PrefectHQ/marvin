import asyncio
import marvin
from . import fun, utilities, meta, jobs, assistants
from marvin import get_logger

logger = get_logger(__name__)


async def install_bots():
    from marvin import Bot

    try:
        for module in [fun, meta, jobs, assistants]:
            for bot in module.__dict__.values():
                if isinstance(bot, Bot):
                    await bot.save(if_exists="update")
    except Exception:
        logger.error("Failed to install bots", exc_info=True)
