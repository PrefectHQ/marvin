from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

import marvin
from marvin.agents.agent import Agent
from marvin.tasks.task import Task
from marvin.thread import Thread
from marvin.utilities.asyncio import run_sync

T = TypeVar("T")


@dataclass(kw_only=True)
class PlanTask:
    id: int
    instructions: str = field(
        metadata={"description": "The instructions or objective for the task"},
    )
    name: str | None = field(
        default=None,
        metadata={
            "description": "A brief name for the task, not more than a few words."
        },
    )
    allow_fail: bool = False
    allow_skip: bool = False
    parent_id: int | None = field(
        default=None,
        metadata={
            "description": "ID of the parent task. Parent tasks can not be completed until all of their children are completed."
        },
    )
    depends_on_ids: list[int] | None = field(
        default=None,
        metadata={
            "description": "IDs of tasks that must be completed before this task can be run."
        },
    )
    agent_ids: list[int] | None = field(
        default=None,
        metadata={
            "description": "IDs of agents who will work on this task. Provide None to work on it yourself."
        },
    )
    tool_ids: list[int] | None = field(
        default=None,
        metadata={
            "description": "IDs of tools to make available to this task. Agents will also have their own tools available."
        },
    )


PROMPT = """
You are a task planner. You have been given some instructions about your
objectives and must produce at least one Marvin Task that, when completed, will
allow you or other AI agents achieve the objective. Each task should represent a
discrete, observable goal, neither too small to be a nuisance or lead to
repetivite work, nor too large to be difficult to manage.

These tasks will be executed by AI agents, like you. Create tasks appropriately.
Do not create tasks like "Validate results" unless a separate validation step is
actually required or helpful. Do not create tasks that require tools that are
not available.
"""


def create_tasks(
    plan: list[PlanTask],
    agent_map: dict[int, Agent],
    tool_map: dict[int, Callable[..., Any]],
    parent_task: Task | None = None,
) -> list[Task]:
    # topological sort so we process children before parents and dependencies before dependents
    sorted_tasks: list[PlanTask] = []
    visited: set[int] = set()
    temp_visited: set[int] = set()  # for cycle detection
    task_map: dict[int, PlanTask] = {task.id: task for task in plan}

    def visit(task_id: int) -> None:
        if task_id in temp_visited:
            raise ValueError(
                f"Cycle detected in task dependencies involving task {task_id}"
            )
        if task_id in visited:
            return

        temp_visited.add(task_id)
        task = task_map[task_id]

        # Visit parent first if it exists
        if task.parent_id is not None:
            if task.parent_id not in task_map:
                raise ValueError(
                    f"Parent task {task.parent_id} not found for task {task_id}"
                )
            visit(task.parent_id)

        # Visit dependencies
        if task.depends_on_ids:
            for dep_id in task.depends_on_ids:
                if dep_id not in task_map:
                    raise ValueError(
                        f"Dependency task {dep_id} not found for task {task_id}"
                    )
                visit(dep_id)

        temp_visited.remove(task_id)
        visited.add(task_id)
        sorted_tasks.append(task)

    # Visit all tasks
    for task in plan:
        if task.id not in visited:
            visit(task.id)

    # Convert PlanTasks to Tasks in dependency order
    tasks: dict[int, Task] = {}
    for plan_task in sorted_tasks:
        task = Task(
            name=plan_task.name,
            instructions=plan_task.instructions,
            agents=(
                [agent_map[id] for id in plan_task.agent_ids]
                if plan_task.agent_ids
                else None
            ),
            result_type=str,
            tools=(
                [tool_map[id] for id in plan_task.tool_ids]
                if plan_task.tool_ids
                else None
            ),
            allow_fail=plan_task.allow_fail,
            allow_skip=plan_task.allow_skip,
            parent=(tasks[plan_task.parent_id] if plan_task.parent_id else parent_task),
            depends_on=(
                [tasks[id] for id in plan_task.depends_on_ids]
                if plan_task.depends_on_ids
                else None
            ),
        )
        tasks.update({plan_task.id: task})

    return list(tasks.values())


async def plan_async(
    instructions: str,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
    available_agents: list[Agent] | None = None,
    tools: list[Callable[..., Any]] | None = None,
    parent_task: Task | None = None,
) -> list[Task]:
    """
    Generate a series of new tasks in order to achieve a goal.

    Args:
        instructions: The objective to achieve.
        agent: The agent to use for planning.
        thread: The thread to use for planning.
        context: Additional context to use for planning.
        available_agents: A list of agents that can be used for planning.
        tools: A list of tools that can be used for planning.

    Returns:
        A list of Marvin Tasks that will allow you or other AI agents to achieve the objective.

    Examples:
        >>> tasks = await marvin.plan_async("Create a new blog post about the latest AI trends.")
        >>> await marvin.run_tasks_async(tasks)
    """
    agent_map = {i: a for i, a in enumerate(available_agents or [])}
    tool_map = {i: t for i, t in enumerate(tools or [])}

    task_context = context or {}
    task_context["Available agents"] = agent_map
    task_context["Available tools"] = tool_map
    prompt = (
        PROMPT
        + f"\n\n Here is the planning objective:\n<objective>\n{instructions}\n</objective>"
    )

    task = marvin.Task[list[PlanTask]](
        name="Planning Task",
        instructions=prompt,
        context=task_context,
        result_type=list[PlanTask],
        agents=[agent] if agent else None,
    )

    tasks = await task.run_async(thread=thread, handlers=[])
    return create_tasks(
        tasks,
        agent_map=agent_map | {None: task.get_actor()},
        tool_map=tool_map,
        parent_task=parent_task,
    )


def plan(
    instructions: str,
    agent: Agent | None = None,
    thread: Thread | str | None = None,
    context: dict[str, Any] | None = None,
    available_agents: list[Agent] | None = None,
    tools: list[Callable[..., Any]] | None = None,
    parent_task: Task | None = None,
) -> list[Task]:
    """
    Generate a series of Marvin Tasks that will allow you or other AI agents to achieve a goal.

    Args:
        instructions: The objective to achieve.
        agent: The agent to use for planning.
        thread: The thread to use for planning.
        context: Additional context to use for planning.
        available_agents: A list of agents that can be used for planning.
        tools: A list of tools that can be used for planning.

    Returns:
        A list of Marvin Tasks that will allow you or other AI agents to achieve the objective.


    Examples:
        >>> tasks = marvin.plan("Create a new blog post about the latest AI trends.")
        >>> marvin.run_tasks(tasks)
    """
    return run_sync(
        plan_async(
            instructions=instructions,
            agent=agent,
            thread=thread,
            context=context,
            available_agents=available_agents,
            tools=tools,
            parent_task=parent_task,
        )
    )
