from marvin import Task


class TestTaskPrompt:
    async def test_task_return_string_prompt(self):
        # default tasks return a list; ensure strings work as well
        class MyTask(Task):
            def get_prompt(self) -> str:
                return 'Say the word "hello"'

        task = MyTask("")
        prompt = task.get_prompt()
        assert prompt == 'Say the word "hello"'
        assert task.run() == "hello"


class TestOptionalResults:
    async def test_optional_result_returns_none(self):
        """Test that tasks with optional result types can actually return None from AI."""
        task = Task(
            instructions="return null",
            result_type=str | None,
        )
        result = await task.run_async()
        assert result is None

    async def test_optional_result_returns_value(self):
        """Test that optional tasks can also return actual values."""
        task = Task(
            instructions='say "hello"',
            result_type=str | None,
        )
        result = await task.run_async()
        assert result == "hello"
