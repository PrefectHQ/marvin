# load nest_asyncio
import nest_asyncio as _nest_asyncio
import asyncio as _asyncio

_nest_asyncio.apply()


# load env vars
from dotenv import load_dotenv as _load_dotenv

_load_dotenv()


# load marvin root objects
from marvin.config import settings
from marvin.utilities.logging import get_logger

# load marvin
from . import utilities, models, infra, api, bots, plugins


from marvin.plugins import Plugin, plugin
from marvin.bots import Bot
from marvin.bots.ai_functions import ai_fn

_logger = get_logger(__name__)
if settings.test_mode:
    _logger.debug_style("Marvin is running in test mode!", style="yellow")
if not settings.openai_model_name.startswith("gpt-4"):
    _logger.info_style(f'Using OpenAI model "{settings.openai_model_name}"')

# set up SQLite if it doesn't exist
infra.db.create_sqlite_db_if_doesnt_exist()
