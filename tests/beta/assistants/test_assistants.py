from unittest.mock import AsyncMock, patch
from marvin.beta.assistants import Assistant
from marvin.tools.assistants import CodeInterpreter
import openai
import pytest


client = openai.AsyncClient(api_key=marvin.settings.openai.api_key.get_secret_value())

# Return a mocked openai client
def mocked_client():
    return client

@pytest.fixture(autouse=True)
def mock_get_client(monkeypatch) -> None:
    """
    Monkeypatch the function to mock the OpenAI client used in the tests.
    """
    monkeypatch.setattr("marvin.utilities.openai.get_openai_client", mocked_client)

@pytest.fixture(autouse=True)
def mock_say(monkeypatch) -> None:
    """
    Monkeypatch the creation of thread runs to prevent actual API calls during testing.
    """
    monkeypatch.setattr(client.beta.threads.runs, "create", AsyncMock())


class TestTools:
    def test_code_interpreter(self) -> None:
        """
        Test that the CodeInterpreter tool generates a random number between 85 and 95.
        """
        ai = Assistant(tools=[CodeInterpreter])
        run = ai.say("use the code interpreter to output a random number between 85 and 95 - you must use print")
        
        # Assert the tool used is 'code_interpreter'
        assert run.steps[0].step_details.tool_calls[0].type == "code_interpreter", "Expected tool call is 'code_interpreter'"

        # Extract the output and validate it's within range
        output = float(run.steps[-2].step_details.tool_calls[0].code_interpreter.outputs[0].logs)
        assert 85 <= output <= 95, f"Expected output to be between 85 and 95, but got {output}"


@pytest.mark.flaky(max_runs=2)
class TestLifeCycle:

    def assert_lifecycle(self, ai: Assistant, mock_create, mock_delete):
        """
        Common assertions for assistant lifecycle.
        """
        assert ai.id, "Expected the assistant to have an id after creation."
        ai.say("hi")
        assert mock_delete.not_called(), "Expected the delete method not to be called during the session."
        assert ai.id, "Expected assistant ID to still exist before deletion."
        ai.delete()
        assert not ai.id, "Expected assistant ID to be None after deletion."
        mock_delete.assert_called_once()

    @patch.object(client.beta.assistants, "delete", wraps=client.beta.assistants.delete)
    @patch.object(client.beta.assistants, "create", wraps=client.beta.assistants.create)
    def test_interactive(self, mock_create, mock_delete) -> None:
        """
        Test that the assistant is auto-created and auto-deleted during interaction.
        """
        ai = Assistant()
        mock_create.assert_not_called()
        assert not ai.id, "Expected the assistant to not have an ID before interaction."
        ai.say("hi")
        assert not ai.id, "Expected the assistant to not have an ID after the first interaction."
        mock_create.assert_called()
        mock_delete.assert_called()

    @patch.object(client.beta.assistants, "delete", wraps=client.beta.assistants.delete)
    @patch.object(client.beta.assistants, "create", wraps=client.beta.assistants.create)
    def test_context_manager(self, mock_create, mock_delete) -> None:
        """
        Test that the assistant is auto-created and auto-deleted only during context management.
        """
        ai = Assistant()
        with ai:
            mock_create.assert_called(), "Expected assistant creation within context."
            assert ai.id, "Expected assistant to have an ID within context."
            ai.say("hi")
            mock_delete.assert_not_called(), "Expected no delete calls within context."
            assert ai.id
        self.assert_lifecycle(ai, mock_create, mock_delete)

    @patch.object(client.beta.assistants, "delete", wraps=client.beta.assistants.delete)
    @patch.object(client.beta.assistants, "create", wraps=client.beta.assistants.create)
    def test_manual_lifecycle(self, mock_create, mock_delete) -> None:
        """
        Test manual assistant creation and deletion.
        """
        ai = Assistant()
        mock_create.assert_not_called()
        ai.create()
        mock_create.assert_called(), "Expected assistant to be created manually."
        self.assert_lifecycle(ai, mock_create, mock_delete)

    def test_load_from_api(self) -> None:
        """
        Test assistant lifecycle when loading from the API.
        """
        api_ai = Assistant()
        api_ai.create()
        api_id = api_ai.id

        # create mocks late to avoid calling above
        with (
            patch.object(client.beta.assistants, "delete", wraps=client.beta.assistants.delete) as mock_delete,
            patch.object(client.beta.assistants, "create", wraps=client.beta.assistants.create) as mock_create,
        ):
            ai = Assistant.load(api_id)
            mock_create.assert_not_called()

            assert ai.id, "Expected assistant to have an ID after loading from API."
            ai.say("hi")
            mock_delete.assert_not_called()
            ai.delete()
            mock_delete.assert_called_once()
