from importlib.metadata import version as _get_version

# load nest_asyncio
import nest_asyncio as _nest_asyncio
import asyncio as _asyncio

loop = _asyncio.get_event_loop_policy().new_event_loop()
_nest_asyncio.apply(loop)

# load env vars
from dotenv import load_dotenv as _load_dotenv

_load_dotenv()

__version__ = _get_version("marvin")

# load marvin root objects
from marvin.config import settings
from marvin.utilities.logging import get_logger

# load marvin
from . import utilities, models, infra, api, bot, plugins, ai_functions


from marvin.plugins import Plugin, plugin
from marvin.bot import Bot
from marvin.ai_functions import ai_fn


_logger = get_logger(__name__)
if settings.test_mode:
    _logger.debug_style("Marvin is running in test mode!", style="yellow")
if not settings.openai_model_name.startswith("gpt-4"):
    _logger.info_style(f'Using OpenAI model "{settings.openai_model_name}"')


# check alembic versions
if settings.database_check_migration_version_on_startup:
    _asyncio.run(infra.database.check_alembic_version())

# load bots
from . import bots
