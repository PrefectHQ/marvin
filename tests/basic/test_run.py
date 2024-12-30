import pytest
from pydantic_ai import UnexpectedModelBehavior
from pydantic_ai.models.test import TestModel

import marvin
import marvin.orchestrator


def test_simple_run(test_model: TestModel):
    task = marvin.Task("Test task")
    test_model.custom_result_args = dict(task_id=task.id, result="hello world")
    result = task.run()
    assert result == "hello world"


def test_simple_run_with_result_type(test_model: TestModel):
    task = marvin.Task("Test task", result_type=int)
    test_model.custom_result_args = dict(task_id=task.id, result=1)
    result = task.run()
    assert result == 1


def test_simple_run_with_wrong_result_type(test_model: TestModel):
    task = marvin.Task("Test task", result_type=int)
    test_model.custom_result_args = dict(task_id=task.id, result="hello world")
    with pytest.raises(UnexpectedModelBehavior):
        task.run()


def test_run_with_thread(test_model: TestModel):
    thread = marvin.Thread()
    result = marvin.run("hello world", thread=thread)
    assert result == "hello world"
