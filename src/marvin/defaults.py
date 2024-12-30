from dataclasses import dataclass

from pydantic_ai.models import Model

import marvin
from marvin import Agent


@dataclass
class Defaults:
    agent: Agent
    model: str | Model


defaults = Defaults(
    agent=Agent(name="Marvin"),
    model=marvin.settings.agent_model,
)
