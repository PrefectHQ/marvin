# load nest_asyncio
import nest_asyncio

nest_asyncio.apply()


# load env vars
from dotenv import load_dotenv

load_dotenv()


__version__ = "0.5.0"

# load marvin root objects
from marvin.config import settings
from marvin.utilities.logging import get_logger

# load marvin
from . import utilities, models, infra, api, bots, plugins


from marvin.plugins import Plugin
from marvin.bots import Bot
from marvin.bots.towel import towel

_logger = get_logger(__name__)
if settings.test_mode:
    _logger.debug_style("Marvin is running in test mode!", style="yellow")
_logger.debug(f'OpenAI model: "{settings.openai_model_name}"')
