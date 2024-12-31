import uuid
from typing import Literal

import pytest
from marvin.agents.agent import Agent
from marvin.tasks.task import Task, TaskState
from marvin.utilities.types import Labels, create_enum, get_labels


class TestClassification:
    def test_auto_enum_conversion(self):
        """Test automatic conversion of list to Enum."""
        task = Task("Choose color", result_type=["red", "green", "blue"])
        assert task._is_classifier()
        assert get_labels(task.result_type) == ("red", "green", "blue")

    def test_literal_classifier(self):
        """Test using Literal as classifier."""
        task = Task("Choose sentiment", result_type=Literal["positive", "negative"])
        assert task._is_classifier()
        assert get_labels(task.result_type) == ("positive", "negative")

    def test_enum_classifier(self):
        """Test using Enum as classifier."""
        Colors = create_enum(["red", "green", "blue"])
        task = Task("Choose color", result_type=Colors)
        assert task._is_classifier()
        assert get_labels(task.result_type) == ("red", "green", "blue")

    def test_multi_label_classifier(self):
        """Test multi-label classification."""
        # Using list[Literal]
        task1 = Task("Choose colors", result_type=list[Literal["red", "green", "blue"]])
        assert task1._is_classifier()
        assert task1.get_result_type() == list[int]

        # Using list[Enum]
        Colors = create_enum(["red", "green", "blue"])
        task2 = Task("Choose colors", result_type=list[Colors])
        assert task2._is_classifier()
        assert task2.get_result_type() == list[int]

    def test_labels_classifier(self):
        """Test using Labels as classifier."""
        # Test single-label
        task = Task("Choose color", result_type=Labels(["red", "green", "blue"]))
        assert task._is_classifier()
        assert get_labels(task.result_type) == ("red", "green", "blue")

        # Test multi-label
        task = Task(
            "Choose colors", result_type=Labels(["red", "green", "blue"], many=True)
        )
        assert task._is_classifier()
        assert task.get_result_type() == list[int]

        # Test validation
        task.mark_successful([0, 2])
        assert task.result == ["red", "blue"]

    def test_classifier_validation(self):
        """Test validation of classifier results."""
        task = Task("Choose color", result_type=["red", "green", "blue"])

        # Valid single index
        task.mark_successful(1)
        assert task.result == "green"

        # Invalid index
        with pytest.raises(ValueError):
            task.mark_successful(3)

        # Invalid type
        with pytest.raises(ValueError):
            task.mark_successful("red")

    def test_multi_label_validation(self):
        """Test validation of multi-label classifier results."""
        task = Task("Choose colors", result_type=list[Literal["red", "green", "blue"]])

        # Valid indices
        task.mark_successful([0, 2])
        assert task.result == ["red", "blue"]

        # Invalid indices
        with pytest.raises(ValueError):
            task.mark_successful([3])

        # Invalid type
        with pytest.raises(ValueError):
            task.mark_successful(0)  # Should be a list

        # Invalid element type
        with pytest.raises(ValueError):
            task.mark_successful(["red"])  # Should be integers

    def test_classifier_prompt_instruction(self):
        """Test that classifier tasks include the additional instruction in their default prompt."""
        task = Task("Choose color", result_type=["red", "green", "blue"])
        prompt = task.get_prompt()
        expected_instruction = (
            "\n\nRespond with the integer index(es) of the labels you're "
            "choosing: {0: 'red', 1: 'green', 2: 'blue'}"
        )
        assert expected_instruction in prompt

        # Test that custom prompts don't include the instruction
        task = Task(
            "Choose color",
            result_type=["red", "green", "blue"],
            prompt_template="Custom prompt: {{task.instructions}}",
        )
        prompt = task.get_prompt()
        assert expected_instruction not in prompt
        assert prompt == "Custom prompt: Choose color"


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
    with pytest.raises(ValueError):
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


def test_task_prompt_customization():
    """Test customizing task prompts."""
    # Test default prompt
    task = Task(
        name="test task",
        instructions="Do something",
        context={"key": "value"},
    )
    prompt = task.get_prompt()
    assert "<id>" in prompt
    assert "<name>test task</name>" in prompt
    assert "<instructions>Do something</instructions>" in prompt
    assert "<context>" in prompt
    assert "<state>pending</state>" in prompt

    # Test custom prompt
    task = Task(
        name="test task",
        instructions="Do something",
        context={"key": "value"},
        prompt_template="Task {{task.name}}: {{task.instructions}}",
    )
    prompt = task.get_prompt()
    assert prompt == "Task test task: Do something"

    # Test custom prompt with conditional logic
    task = Task(
        name="test task",
        instructions="Do something",
        context={"key": "value"},
        prompt_template="""
            {% if task.name %}NAME: {{task.name}}{% endif %}
            INSTRUCTIONS: {{task.instructions}}
            {% if task.context %}CONTEXT: {{task.context}}{% endif %}
        """.strip(),
    )
    prompt = task.get_prompt()
    assert "NAME: test task" in prompt
    assert "INSTRUCTIONS: Do something" in prompt
    assert "CONTEXT: {'key': 'value'}" in prompt

    # Test accessing task methods in template
    task = Task(
        instructions="Do something",
        prompt_template="Task is complete: {{task.is_complete()}}",
    )
    prompt = task.get_prompt()
    assert prompt == "Task is complete: False"
    task.mark_successful()
    prompt = task.get_prompt()
    assert prompt == "Task is complete: True"


def test_task_mark_running():
    """Test marking task as running."""
    task = Task(instructions="Test running")
    assert task.state == TaskState.PENDING
    task.mark_running()
    assert task.state == TaskState.RUNNING
