from contextlib import contextmanager
from dataclasses import dataclass

from pydantic_ai.models import KnownModelName, Model
from typing_extensions import Unpack

import marvin
from marvin import Agent


@dataclass
class Defaults:
    agent: Agent
    model: KnownModelName | Model
    memory_provider: str


defaults = Defaults(
    agent=Agent(name="Marvin"),
    model=marvin.settings.agent_model,
    memory_provider=marvin.settings.memory_provider,
)


@contextmanager
def override_defaults(**kwargs: Unpack[Defaults]):
    """Temporarily override default settings.

    Any attribute of the defaults object can be temporarily overridden by passing
    it as a keyword argument.

    Example:
        >>> with override_defaults(model="gpt-4", agent=Agent(name="Custom")):
        ...     # code that uses the temporary defaults
        ...     pass

    """
    original_values = {}

    for key, value in kwargs.items():
        if not hasattr(defaults, key):
            raise ValueError(f"Invalid default setting: {key}")
        original_values[key] = getattr(defaults, key)
        setattr(defaults, key, value)

    try:
        yield
    finally:
        for key, value in original_values.items():
            setattr(defaults, key, value)
