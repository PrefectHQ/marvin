import inspect
import os
from datetime import datetime
from functools import partial
from typing import Any
from zoneinfo import ZoneInfo

from jinja2 import Environment as JinjaEnvironment
from jinja2 import PackageLoader, StrictUndefined, select_autoescape
from pydantic_core import to_json


def _is_agent(x: object) -> bool:
    from marvin.agents.agent import Agent

    return isinstance(x, Agent)


def _is_team(x: object) -> bool:
    from marvin.agents.team import Team

    return isinstance(x, Team)


def _pretty_print(x: object) -> str:
    return to_json(x, indent=4).decode("utf-8")


global_fns: dict[str, Any] = {
    "now": partial(datetime.now, tz=ZoneInfo("UTC")),
    "inspect": inspect,
    "getcwd": os.getcwd,
    "zip": zip,
    "is_agent": _is_agent,
    "is_team": _is_team,
    "pretty_print": _pretty_print,
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
