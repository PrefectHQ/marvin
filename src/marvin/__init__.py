from importlib.metadata import version as _version

# necessary imports
from marvin.settings import settings
from marvin.engine.database import ensure_tables_exist

# core classes
from marvin.engine.thread import Thread
from marvin.agents.agent import Agent
from marvin.tasks.task import Task
from marvin.memory.memory import Memory

# public functions
from marvin.instructions import instructions
from marvin.run import run, run_async, run_tasks_async
from marvin.defaults import defaults

# marvin fns
from marvin.fns.classify import classify, classify_async
from marvin.fns.extract import extract, extract_async
from marvin.fns.cast import cast, cast_async
from marvin.fns.generate import generate, generate_async
from marvin.fns.fn import fn

ensure_tables_exist()

__version__ = _version("marvin")

__all__ = [
    "Agent",
    "Memory",
    "Task",
    "Thread",
    "cast",
    "cast_async",
    "classify",
    "classify_async",
    "defaults",
    "extract",
    "extract_async",
    "fn",
    "generate",
    "generate_async",
    "instructions",
    "run",
    "run_async",
    "run_tasks_async",
    "settings",
]
