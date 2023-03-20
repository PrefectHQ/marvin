# load env vars
from dotenv import load_dotenv

load_dotenv()

# load nest_asyncio
import nest_asyncio

nest_asyncio.apply()

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
