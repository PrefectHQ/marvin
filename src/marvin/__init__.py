# load nest_asyncio
import nest_asyncio

nest_asyncio.apply()


# load env vars
from dotenv import load_dotenv

load_dotenv()


# load version
import pkg_resources

__version__ = pkg_resources.require("marvin")[0].version

# load marvin root objects
from marvin.config import settings
from marvin.utilities.logging import get_logger

# load marvin
from . import utilities, models, infra, api, bots, plugins, server, cli


from marvin.plugins import Plugin
from marvin.bots import Bot

_logger = get_logger(__name__)
if settings.test_mode:
    _logger.debug_style("Marvin is running in test mode!", style="yellow")
_logger.debug(f'OpenAI model: "{settings.openai_model_name}"')
