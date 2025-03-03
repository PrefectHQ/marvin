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
