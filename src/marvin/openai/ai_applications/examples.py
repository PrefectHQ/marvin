from datetime import datetime

from pydantic import BaseModel, Field

import marvin
import marvin.openai
import marvin.openai.tools
from marvin.openai.ai_applications import AIApplication

marvin.settings.log_level = "DEBUG"
marvin.settings.llm_model = "gpt-3.5-turbo-0613"
# marvin.settings.llm_model = "gpt-4-0613"


class ToDo(BaseModel):
    title: str
    description: str = None
    due_date: datetime = None
    done: bool = False


class ToDoState(BaseModel):
    todos: list[ToDo] = []


todo_app = AIApplication(
    name="ToDo app",
    description="A simple to-do tracker. Users will add, update, and complete tasks.",
    state=ToDoState(),
    ai_state_enabled=False,
)


class EngState(BaseModel):
    files: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "A description of the paths in the filesystem, including any detail (like"
            " key functions) needed to understand the program's operation"
        ),
    )


ROOT_DIR = "/Users/jeremiah/Desktop/marvin_test"

cto_app = AIApplication(
    name="CTO",
    description=f"""
        # Overview 
         
        An expert software developer. Writes elegant, readable, user-friendly
        code. Strives to write usable code and cover likely edge cases
        responsibly to create the best developer experience possible. Remember
        to write all files to disk, don't just show outputs to the user. Use a
        readme and documentation to track any important details, including
        details you may need to remember yourself.
        
        # Constraints 
        
        This application should ONLY modify files in {ROOT_DIR} and NEVER
        anywhere else. When generating or editing code, make sure to write it to
        the filesystem rather than just showing it to the user. When starting,
        check if there are existing files to avoid accidental overwrites.
        """,
    state=EngState(),
    tools=[
        marvin.openai.tools.filesystem.ListFiles(root_dir=ROOT_DIR),
        marvin.openai.tools.filesystem.ReadFiles(root_dir=ROOT_DIR),
        marvin.openai.tools.filesystem.WriteFiles(
            root_dir=ROOT_DIR, require_confirmation=False
        ),
        marvin.openai.tools.python.Python(require_confirmation=False),
        marvin.openai.tools.shell.Shell(
            require_confirmation=False, working_directory=ROOT_DIR
        ),
    ],
)


class GameState(BaseModel):
    mission: str = None
    notes: list[str] = []
    environment: str = None


game_app = AIApplication(
    name="sw game",
    description=(
        "A simple text-based RPG that guides the user through an interactive mission in"
        " the Star Wars universe. Take any input from the user but do not ask any"
        " questions, just begin a highly engrossing and cinematic story. Make sure to"
        " move the story along to keep it interesting and engaging. Write"
        " highly-detailed narratives that always keep the user engaged and moving"
        " forward."
    ),
    state=GameState(),
)


nested_app = AIApplication(
    name="test app",
    description=(
        "An application that can convert between different units of measurement."
    ),
    state_enabled=False,
    tools=[
        AIApplication(
            description="An application that only converts feet to inches.",
            state_enabled=False,
        ),
        AIApplication(
            description="An application that only converts months to days.",
            state_enabled=False,
        ),
    ],
)
