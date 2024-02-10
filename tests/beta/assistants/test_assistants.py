import pytest
from marvin.beta.assistants import Assistant
from marvin.utilities.openai import get_openai_client


@pytest.fixture(autouse=True)
async def clean_up_assistants():
    yield
    client = get_openai_client(is_async=True)
    for assistant in (await client.beta.assistants.list()).data:
        if assistant.name.startswith("marvin-test-assistant"):
            await client.beta.assistants.delete(assistant.id)


class TestLifecycleManagement:
    def test_say_doesnt_delete_assistant(self):
        assistant = Assistant(name="marvin-test-assistant")
        assistant.say("Hello, world!")
        existing_assistant = Assistant.load(assistant_id=assistant.id)

        assert existing_assistant.id == assistant.id
        assert isinstance(existing_assistant, Assistant)
