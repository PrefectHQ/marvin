from datetime import datetime

from marvin import AIApplication
from pydantic import BaseModel, Field


class ToDo(BaseModel):
    title: str
    description: str = None
    due_date: datetime = None
    done: bool = False


class ToDoState(BaseModel):
    todos: list[ToDo] = []


class ToDoApp(AIApplication):
    state: ToDoState = Field(default_factory=ToDoState)
    description: str = """
        A simple to-do tracker. Users will give instructions to add, remove, and
        update their to-dos.
        """
    plan_enabled: bool = False


__all__ = ["ToDoApp"]
