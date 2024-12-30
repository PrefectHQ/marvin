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


__version__ = _version("marvin")
