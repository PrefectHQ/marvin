import inspect
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from jinja2 import Environment as JinjaEnvironment
from jinja2 import PackageLoader, StrictUndefined, select_autoescape

global_fns = {
    "now": lambda: datetime.now(ZoneInfo("UTC")),
    "inspect": inspect,
    "getcwd": os.getcwd,
    "zip": zip,
}

prompt_env = JinjaEnvironment(
    loader=PackageLoader("marvin", "templates"),
    autoescape=select_autoescape(default_for_string=False),
    trim_blocks=True,
    lstrip_blocks=True,
    auto_reload=True,
    undefined=StrictUndefined,
)

prompt_env.globals.update(global_fns)
