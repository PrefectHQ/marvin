from typing import Literal, Optional

from pydantic import BaseModel, Field

from marvin.beta.assistants import Thread
from marvin.tools.assistants import AssistantTool
from marvin.utilities.jinja import Environment as JinjaEnvironment

from .applications import Application, State

PLANNER_INSTRUCTIONS = """
To assist you with long-term planning and keeping track of multiple threads, you
must always update your plan before and (if appropriate) after every response.
Your plan is a list of tasks that describe your plans in fine detail. Use
`parent` and `depends_on` to describe the relationships between tasks. Use
`outcome` to record the outcome of each finished task. Always update task states
appropriately. Note you do not need to create tasks for direct responses to the
user (e.g. those that would be immediately completed). You can clean up the task
list over time to keep it manageable. 

Your current plan is:

{{self_.plan.render()}}

"""


class Task(BaseModel):
    id: int = Field(description="A unique ID")
    description: str = Field(description="A brief description of the task")
    state: Literal[
        "planned", "in_progress", "completed", "canceled", "failed"
    ] = "planned"
    parents: list[int] = Field(
        [], description="IDs of tasks that are parents of this task"
    )
    depends_on: list[int] = Field(
        [], description="IDs of tasks that this task depends on"
    )
    outcome: Optional[str] = Field(
        None, description="The outcome of a task (only when completed or failed)"
    )


class TaskList(BaseModel):
    tasks: list[Task] = Field([], description="The list of tasks")


class AIPlanner(Application):
    plan: State = Field(default_factory=lambda: State(value=TaskList()))

    def get_instructions(self, thread: Thread = None) -> str:
        instructions = super().get_instructions()
        return JinjaEnvironment.render(
            instructions + "\n\n" + PLANNER_INSTRUCTIONS, self_=self
        )

    def get_tools(self) -> list[AssistantTool]:
        tools = super().get_tools()
        tools.append(self.plan.as_tool(name="plan"))
        return tools
