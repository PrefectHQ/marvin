from marvin.settings import AssistantSettings, Settings, SpeechSettings
from pydantic_settings import SettingsConfigDict


def test_api_key_initialization_from_env(env):
    test_api_key = "test_api_key_123"
    env.set("MARVIN_OPENAI_API_KEY", test_api_key)

    temp_model_config = SettingsConfigDict(env_prefix="marvin_")
    settings = Settings(model_config=temp_model_config)

    assert settings.openai.api_key.get_secret_value() == test_api_key


def test_runtime_api_key_override(env):
    override_api_key = "test_api_key_456"
    env.set("MARVIN_OPENAI_API_KEY", override_api_key)

    temp_model_config = SettingsConfigDict(env_prefix="marvin_")
    settings = Settings(model_config=temp_model_config)

    assert settings.openai.api_key.get_secret_value() == override_api_key

    settings.openai.api_key = "test_api_key_789"

    assert settings.openai.api_key.get_secret_value() == "test_api_key_789"


class TestSpeechSettings:
    def test_speech_settings_default(self):
        settings = SpeechSettings()
        assert settings.model == "tts-1-hd"
        assert settings.voice == "alloy"
        assert settings.response_format == "mp3"
        assert settings.speed == 1.0


class TestAssistantSettings:
    def test_assistant_settings_default(self):
        settings = AssistantSettings()
        assert settings.model == "gpt-4-1106-preview"
