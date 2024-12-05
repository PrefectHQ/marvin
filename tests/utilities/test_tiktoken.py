import os
from unittest.mock import MagicMock, patch

from marvin.settings import ChatCompletionSettings, settings, temporary_settings


def test_tiktoken_cache_dir_setting(tmp_path):
    with temporary_settings(
        openai__chat__completions__tiktoken__cache_dir=str(tmp_path)
    ):
        _ = settings.openai.chat.completions.encoder
        assert os.environ.get("TIKTOKEN_CACHE_DIR") == str(tmp_path)

    # Check that the environment is cleaned up after the test
    assert "TIKTOKEN_CACHE_DIR" not in os.environ


def test_tiktoken_default_behavior():
    # Test with default settings (no cache dir, SSL verification enabled)
    with patch("tiktoken.encoding_for_model") as mock_encoding:
        mock_encoder = MagicMock()
        mock_encoding.return_value = mock_encoder

        chat_settings = ChatCompletionSettings()
        _ = chat_settings.encoder

        # Check that TIKTOKEN_CACHE_DIR is not set
        assert "TIKTOKEN_CACHE_DIR" not in os.environ

        # Check that SSL verification is not modified
        import ssl

        assert ssl._create_default_https_context != ssl._create_unverified_context

        mock_encoding.assert_called_once_with(chat_settings.model)
