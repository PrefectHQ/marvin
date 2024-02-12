from unittest.mock import patch

import marvin
import openai
import pytest
from marvin.beta.assistants import Assistant

client = openai.AsyncClient(api_key=marvin.settings.openai.api_key.get_secret_value())


def mocked_client():
    return client


@pytest.fixture(autouse=True)
def mock_get_client(monkeypatch):
    # Use monkeypatch to replace get_client with special_get_client
    monkeypatch.setattr("marvin.utilities.openai.get_openai_client", mocked_client)


class TestLifeCycle:
    @patch.object(client.beta.assistants, "delete", wraps=client.beta.assistants.delete)
    @patch.object(client.beta.assistants, "create", wraps=client.beta.assistants.create)
    def test_interactive(self, mock_create, mock_delete):
        """auto-create and auto-delete on interaction"""
        ai = Assistant()
        mock_create.assert_not_called()
        assert not ai.id
        response = ai.say("repeat the word hi")
        assert response
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
            ai.say("repeat the word hi")
            mock_delete.assert_not_called()
            ai.say("repeat the word hi")
            mock_delete.assert_not_called()
            assert ai.id
        assert not ai.id
        mock_delete.assert_called_once()
        mock_create.assert_called_once()

    @patch.object(client.beta.assistants, "delete", wraps=client.beta.assistants.delete)
    @patch.object(client.beta.assistants, "create", wraps=client.beta.assistants.create)
    def test_manual_lifecycle(self, mock_create, mock_delete):
        """manual create and delete"""
        ai = Assistant()
        mock_create.assert_not_called()
        ai.create()
        mock_create.assert_called()
        assert ai.id
        ai.say("repeat the word hi")
        mock_delete.assert_not_called()
        ai.say("repeat the word hi")
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
            ai.say("repeat the word hi")
            mock_delete.assert_not_called()
            ai.say("repeat the word hi")
            mock_delete.assert_not_called()
            assert ai.id
            ai.delete()
            assert not ai.id
            mock_delete.assert_called_once()
            mock_create.assert_not_called()
