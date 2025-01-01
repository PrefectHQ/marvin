from importlib.metadata import version as _version

# necessary imports
from marvin.settings import settings
import marvin.engine

# core classes
from marvin.engine.thread import Thread
from marvin.agents.agent import Agent
from marvin.tasks.task import Task

# public functions
from marvin.instructions import instructions
from marvin.run import run, run_async, run_tasks_async
from marvin.defaults import defaults, override_defaults

# marvin fns
from marvin.fns.classify import classify, classify_async
from marvin.fns.extract import extract, extract_async
from marvin.fns.cast import cast, cast_async
from marvin.fns.generate import generate, generate_async
from marvin.fns.fn import fn

__version__ = _version("marvin")
