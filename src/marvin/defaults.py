from dataclasses import dataclass
import marvin
from marvin import Agent


@dataclass
class Defaults:
    agent: Agent
    model: str


defaults = Defaults(
    agent=Agent(name="Marvin"),
    model=marvin.settings.agent_model,
)
