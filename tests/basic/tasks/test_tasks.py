import enum
import uuid
from typing import Literal

import pytest
from marvin.agents.agent import Agent
from marvin.tasks.task import Task, TaskState
from marvin.utilities.types import Labels


class Colors(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class TestClassification:
    def test_auto_enum_conversion(self):
        """Test automatic conversion of list to Labels."""
        task = Task("Choose color", result_type=["red", "green", "blue"])
        assert task.is_classifier()
        assert isinstance(task.result_type, Labels)
        assert task.result_type.labels == ("red", "green", "blue")

    def test_literal_classifier(self):
        """Test using Literal as classifier."""
        task = Task("Choose sentiment", result_type=Literal["positive", "negative"])
        assert task.is_classifier()

        # Test validation returns raw values
        task.mark_successful(0)
        assert task.result == "positive"
        task.mark_successful(1)
        assert task.result == "negative"

    def test_enum_classifier(self):
        """Test using Enum as classifier."""
        task = Task("Choose color", result_type=Colors)
        assert task.is_classifier()

        # Test validation returns enum members
        task.mark_successful(0)
        assert task.result == Colors.RED
        assert task.result.value == "red"

    def test_raw_list_classifier(self):
        """Test using raw list as classifier."""
        task = Task("Choose color", result_type=["red", "green", "blue"])
        assert task.is_classifier()
        assert isinstance(task.result_type, Labels)
        assert task.result_type.labels == ("red", "green", "blue")

        # Test validation returns raw values
        task.mark_successful(0)
        assert task.result == "red"
        task.mark_successful(1)
        assert task.result == "green"

    def test_multi_label_classifier(self):
        """Test multi-label classification."""
        # Using list[Literal]
        task1 = Task("Choose colors", result_type=list[Literal["red", "green", "blue"]])
        assert task1.is_classifier()
        assert task1.get_result_type() == list[int]

        # Test validation returns raw values
        task1.mark_successful([0, 2])
        assert task1.result == ["red", "blue"]

        # Using list[Enum]
        task2 = Task("Choose colors", result_type=list[Colors])
        assert task2.is_classifier()
        assert task2.get_result_type() == list[int]

        # Test validation returns enum members
        task2.mark_successful([0, 2])
        assert task2.result == [Colors.RED, Colors.BLUE]
        assert [v.value for v in task2.result] == ["red", "blue"]

    def test_labels_classifier(self):
        """Test using list[list] syntax for multi-label classification."""
        # Test single-label with raw list
        task = Task("Choose color", result_type=["red", "green", "blue"])
        assert task.is_classifier()
        assert isinstance(task.result_type, Labels)
        assert task.result_type.labels == ("red", "green", "blue")

        # Test validation returns raw values
        task.mark_successful(0)
        assert task.result == "red"

        # Test multi-label with list[list]
        task = Task("Choose colors", result_type=[["red", "green", "blue"]])
        assert task.is_classifier()
        assert task.get_result_type() == list[int]

        # Test validation returns raw values
        task.mark_successful([0, 2])
        assert task.result == ["red", "blue"]

    def test_classifier_validation_errors(self):
        """Test validation error cases for classifiers."""
        # Test single-label
        task = Task("Choose color", result_type=["red", "green", "blue"])

        with pytest.raises(ValueError, match="Expected an integer index"):
            task.mark_successful("red")  # Wrong type
        with pytest.raises(ValueError, match="between 0 and"):
            task.mark_successful(3)  # Out of range
        with pytest.raises(ValueError, match="Expected an integer index"):
            task.mark_successful([0])  # List when single expected

        # Test multi-label
        task = Task("Choose colors", result_type=[["red", "green", "blue"]])

        with pytest.raises(ValueError, match="Expected a list of indices"):
            task.mark_successful(0)  # Single when list expected
        with pytest.raises(ValueError, match="All elements must be integers"):
            task.mark_successful(["red"])  # Wrong element type
        with pytest.raises(ValueError, match="between 0 and"):
            task.mark_successful([3])  # Out of range index

    def test_classifier_prompt_instruction(self):
        """Test that classifier tasks include the additional instruction in their default prompt."""
        task = Task("Choose color", result_type=["red", "green", "blue"])
        prompt = task.get_prompt()
        expected_instruction = (
            "\n\nRespond with the integer index(es) of the labels you're "
            "choosing: {0: \"'red'\", 1: \"'green'\", 2: \"'blue'\"}"
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

    def test_classifier_edge_cases(self):
        """Test edge cases for classifier types."""
        # Empty lists
        with pytest.raises(ValueError):
            Task("Empty", result_type=[])
        with pytest.raises(ValueError):
            Task("Empty nested", result_type=[[]])

        # Wrong nested format
        with pytest.raises(ValueError):
            Task("Wrong nesting", result_type=[[], []])

        # Mixed types are allowed
        task = Task("Mixed", result_type=[1, "red", True])
        assert task.is_classifier()
        assert isinstance(task.result_type, Labels)
        assert task.result_type.labels == (1, "red", True)

    def test_type_preservation(self):
        """Test that type hints are preserved for IDE support."""
        # Enum types
        task1: Task[Colors] = Task("Colors", result_type=Colors)
        assert task1.is_classifier()
        task1.mark_successful(0)
        assert isinstance(task1.result, Colors)
        assert task1.result == Colors.RED

        # Multi-label enum
        task2: Task[list[Colors]] = Task("Colors", result_type=list[Colors])
        assert task2.is_classifier()
        task2.mark_successful([0, 1])
        assert isinstance(task2.result, list)
        assert all(isinstance(x, Colors) for x in task2.result)
        assert task2.result == [Colors.RED, Colors.GREEN]

        # Literal types
        task3: Task[Literal["a", "b"]] = Task("Literal", result_type=Literal["a", "b"])
        assert task3.is_classifier()
        task3.mark_successful(0)
        assert isinstance(task3.result, str)
        assert task3.result == "a"

    def test_validation_edge_cases(self):
        """Test edge cases for validation."""
        # Single-label
        task = Task("Choose color", result_type=["red", "green", "blue"])

        with pytest.raises(ValueError):
            task.mark_successful(None)  # None value

        # Multi-label
        task = Task("Choose colors", result_type=[["red", "green", "blue"]])

        with pytest.raises(ValueError):
            task.mark_successful([])  # Empty list
        with pytest.raises(ValueError):
            task.mark_successful(None)  # None value
        with pytest.raises(ValueError):
            task.mark_successful([0, 0])  # Duplicate indices


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
    assert "<state>TaskState.PENDING</state>" in prompt

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
