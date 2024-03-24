from unittest.mock import AsyncMock, patch

import marvin
import openai
import pytest
from marvin.beta.assistants import Assistant
from marvin.tools.assistants import CodeInterpreter

client = openai.AsyncClient(api_key=marvin.settings.openai.api_key.get_secret_value())


def mocked_client():
    return client


@pytest.fixture(autouse=True)
def mock_get_client(monkeypatch):
    # Use monkeypatch to replace get_client with special_get_client
    monkeypatch.setattr("marvin.utilities.openai.get_openai_client", mocked_client)


@pytest.fixture(autouse=True)
def mock_say(monkeypatch):
    monkeypatch.setattr(client.beta.threads.runs, "create", AsyncMock())


class TestTools:
    def test_code_interpreter(self):
        ai = Assistant(tools=[CodeInterpreter])
        run = ai.say(
            "use the code interpreter to compute a random number between 85 and 95"
        )
        assert run.steps[0].step_details.tool_calls[0].type == "code_interpreter"
        output = float(
            run.steps[-2].step_details.tool_calls[0].code_interpreter.outputs[0].logs
        )
        assert 85 <= output <= 95


class TestLifeCycle:
    @patch.object(client.beta.assistants, "delete", wraps=client.beta.assistants.delete)
    @patch.object(client.beta.assistants, "create", wraps=client.beta.assistants.create)
    def test_interactive(self, mock_create, mock_delete):
        """auto-create and auto-delete on interaction"""
        ai = Assistant()
        mock_create.assert_not_called()
        assert not ai.id
        ai.say("hi")
        assert not ai.id
        mock_create.assert_called()
        mock_delete.assert_called()

    @patch.object(client.beta.assistants, "delete", wraps=client.beta.assistants.delete)
    @patch.object(client.beta.assistants, "create", wraps=client.beta.assistants.create)
    def test_context_manager(self, mock_create, mock_delete):
        """auto-create and auto-delete on context only"""
        ai = Assistant()
        with ai:
            mock_create.assert_called()
            assert ai.id
            ai.say("hi")
            mock_delete.assert_not_called()
            ai.say("hi")
            mock_delete.assert_not_called()
            assert ai.id
        assert not ai.id
        mock_delete.assert_called_once()
        mock_create.assert_called_once()

    @pytest.mark.flaky(reruns=2)
    @patch.object(client.beta.assistants, "delete", wraps=client.beta.assistants.delete)
    @patch.object(client.beta.assistants, "create", wraps=client.beta.assistants.create)
    def test_manual_lifecycle(self, mock_create, mock_delete):
        """manual create and delete"""
        ai = Assistant()
        mock_create.assert_not_called()
        ai.create()
        mock_create.assert_called()
        assert ai.id
        ai.say("hi")
        mock_delete.assert_not_called()
        ai.say("hi")
        mock_delete.assert_not_called()
        assert ai.id
        ai.delete()
        assert not ai.id
        mock_delete.assert_called_once()
        mock_create.assert_called_once()

    def test_load_from_api(self):
        """fully manual delete"""

        api_ai = Assistant()
        api_ai.create()
        api_id = api_ai.id

        # create mocks late to avoid calling above
        with (
            patch.object(
                client.beta.assistants, "delete", wraps=client.beta.assistants.delete
            ) as mock_delete,
            patch.object(
                client.beta.assistants, "create", wraps=client.beta.assistants.create
            ) as mock_create,
        ):
            ai = Assistant.load(api_id)
            mock_create.assert_not_called()

            assert ai.id
            ai.say("hi")
            mock_delete.assert_not_called()
            ai.say("hi")
            mock_delete.assert_not_called()
            assert ai.id
            ai.delete()
            assert not ai.id
            mock_delete.assert_called_once()
            mock_create.assert_not_called()
