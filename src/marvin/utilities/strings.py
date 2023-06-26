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
    # Monday, 26 June 2023 at 09:00:00 PM UTC
    dt=lambda: datetime.now(ZoneInfo("UTC")).strftime("%A, %d %B %Y at %I:%M:%S %p %Z"),
)
