import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from jinja2 import ChoiceLoader, Environment, StrictUndefined, select_autoescape

jinja_env = Environment(
    loader=ChoiceLoader(
        [
            # PackageLoader("marvin", "prompts")
        ]
    ),
    autoescape=select_autoescape(default_for_string=False),
    trim_blocks=True,
    lstrip_blocks=True,
    enable_async=True,
    auto_reload=True,
    undefined=StrictUndefined,
)

jinja_env.globals.update(
    zip=zip,
    arun=asyncio.run,
    now=lambda: datetime.now(ZoneInfo("UTC")),
)
