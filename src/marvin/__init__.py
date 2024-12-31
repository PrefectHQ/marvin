from importlib.metadata import version as _version

# necessary imports
from marvin.settings import settings

# core classes
from marvin.engine.thread import Thread
from marvin.agents.agent import Agent
from marvin.tasks.task import Task

# public functions
from marvin.instructions import instructions
from marvin.run import run, run_async, run_tasks_async
from marvin.defaults import defaults, override_defaults

# marvin fns
from marvin.fns.classify import classify
from marvin.fns.extract import extract
from marvin.fns.cast import cast
from marvin.fns.generate import generate
from marvin.fns.fn import fn

__version__ = _version("marvin")

__all__ = [
    "settings",
    "Thread",
    "Agent",
    "Task",
    "instructions",
    "run",
    "run_async",
    "run_tasks_async",
    "defaults",
    "override_defaults",
    "classify",
    "extract",
    "cast",
    "generate",
    "fn",
]
