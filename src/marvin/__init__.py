from importlib.metadata import version as _version

# necessary imports
from marvin.settings import settings
from marvin.database import init_database

# core classes
from marvin.thread import Thread
from marvin.agents.agent import Agent
from marvin.tasks.task import Task
from marvin.memory.memory import Memory

# public access
from marvin.instructions import instructions
from marvin.defaults import defaults
from marvin.agents.team import Swarm

# marvin fns
from marvin.fns.run import run, run_async, run_tasks_async, run_tasks
from marvin.fns.classify import classify, classify_async
from marvin.fns.extract import extract, extract_async
from marvin.fns.cast import cast, cast_async
from marvin.fns.generate import (
    generate,
    generate_async,
    generate_schema,
    generate_schema_async,
)
from marvin.fns.fn import fn
from marvin.fns.say import say, say_async
from marvin.fns.summarize import summarize, summarize_async
from marvin.fns.plan import plan, plan_async

# Initialize the database on import
init_database()

__version__ = _version("marvin")

__all__ = [
    "Agent",
    "Memory",
    "Swarm",
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
    "generate_schema",
    "generate_schema_async",
    "instructions",
    "plan",
    "plan_async",
    "run",
    "run_async",
    "run_tasks",
    "run_tasks_async",
    "settings",
    "say",
    "say_async",
    "summarize",
    "summarize_async",
]
