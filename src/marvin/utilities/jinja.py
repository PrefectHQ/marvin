import inspect
import json
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from jinja2 import Environment as JinjaEnvironment
from jinja2 import PackageLoader, StrictUndefined, select_autoescape

import marvin

global_fns: dict[str, Any] = {
    "now": lambda: datetime.now(ZoneInfo("UTC")),
    "inspect": inspect,
    "getcwd": os.getcwd,
    "zip": zip,
    "is_agent": lambda x: isinstance(x, marvin.agents.agent.Agent),
    "is_team": lambda x: isinstance(x, marvin.agents.team.Team),
    "pretty_print": lambda x: json.dumps(x, indent=4),
}

jinja_env = JinjaEnvironment(
    loader=PackageLoader("marvin", "templates"),
    autoescape=select_autoescape(default_for_string=False),
    trim_blocks=True,
    lstrip_blocks=True,
    auto_reload=True,
    undefined=StrictUndefined,
)

jinja_env.globals.update(global_fns)
