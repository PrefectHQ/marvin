from datetime import datetime

from pydantic import BaseModel

import marvin
import marvin.openai
import marvin.openai.tools
from marvin.openai.ai_applications import AIApplication

marvin.settings.log_level = "DEBUG"
marvin.settings.llm_model = "gpt-3.5-turbo-0613"


class ToDo(BaseModel):
    title: str
    description: str = None
    due_date: datetime = None
    done: bool = False


class ToDoState(BaseModel):
    todos: list[ToDo] = []


todo_app = AIApplication(
    description=(
        "A simple to-do tracker. Users will add, update, and complete tasks. Do not"
        " create duplicate tasks."
    ),
    state=ToDoState(),
)


from marvin.openai.tools import filesystem, python, shell


class EngState(BaseModel):
    paths: list[str] = []
    program_description: str = None
    notes: list[str] = []


ROOT_DIR = "/Users/jeremiah/Desktop/marvin_test"
test_app = AIApplication(
    description=(
        "An assistant software developer, expert in Python. Has access to any files at"
        f" {ROOT_DIR}. When generating or editing code, make sure to write it to the"
        " filesystem rather than just showing it to the user. When starting, check if"
        " there are existing files to avoid accidental overwrites."
    ),
    state=EngState(),
    tools=[
        filesystem.ListFiles(root_dir=ROOT_DIR),
        filesystem.ReadFiles(root_dir=ROOT_DIR),
        filesystem.WriteFiles(root_dir=ROOT_DIR),
        python.Python(),
        shell.Shell(),
    ],
)
