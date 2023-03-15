# load env vars
from dotenv import load_dotenv

load_dotenv()

# load nest_asyncio
import nest_asyncio

nest_asyncio.apply()

# load marvin root objects
from marvin.config import settings
from marvin.utilities.logging import get_logger

# load marvin
from . import utilities, infra, bots, plugins, cli

from marvin.bots import Bot
