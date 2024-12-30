import uuid

import pytest
import pydantic_ai

from marvin.agents.agent import Agent
from marvin.tasks.task import Task, TaskState


def test_task_initialization():
    """Test basic task initialization."""
    task = Task(instructions="Test task")
    assert isinstance(task.id, uuid.UUID)
    assert task.instructions == "Test task"
    assert task.result_type == str
    assert task.state == TaskState.PENDING
    assert task.result is None
    assert task.context == {}
    assert task.name is None
    assert task._children == []
    assert task.parent is None


def test_task_with_agent():
    """Test task with custom agent."""
    agent = Agent()
    task = Task(instructions="Test with agent", agent=agent)
    assert task.agent is agent
    assert task.get_agent() is agent


def test_task_get_default_agent():
    """Test getting default agent when none specified."""
    task = Task(instructions="Test default agent")
    assert isinstance(task.get_agent(), Agent)


def test_task_mark_successful():
    """Test marking task as successful."""
    task = Task(instructions="Test success")
    task.mark_successful("test result")
    assert task.state == TaskState.SUCCESSFUL
    assert task.result == "test result"


def test_task_mark_failed():
    """Test marking task as failed."""
    task = Task(instructions="Test failure")
    error_msg = "Test error"
    task.mark_failed(error_msg)
    assert task.state == TaskState.FAILED
    assert task.result == error_msg


def test_task_with_custom_validator():
    """Test task with custom result validator."""

    def validate_positive(x: int) -> int:
        if x <= 0:
            raise ValueError("Number must be positive")
        return x

    task = Task(
        instructions="Test validation",
        result_type=int,
        result_validator=validate_positive,
    )

    # Test successful validation
    task.mark_successful(5)
    assert task.result == 5

    # Test failed validation
    with pytest.raises(pydantic_ai.ModelRetry):
        task.mark_successful(-1)


def test_task_parent_child_relationship():
    """Test parent-child task relationship."""
    parent_task = Task(instructions="Parent task")
    child_task = Task(instructions="Child task", parent=parent_task)

    assert child_task.parent is parent_task
    parent_task._children.append(child_task)
    assert child_task in parent_task._children


def test_task_with_context():
    """Test task with context data."""
    context = {"key": "value"}
    task = Task(instructions="Test context", context=context)
    assert task.context == context


def test_task_mark_running():
    """Test marking task as running."""
    task = Task(instructions="Test running")
    assert task.state == TaskState.PENDING
    task.mark_running()
    assert task.state == TaskState.RUNNING
