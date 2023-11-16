from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from marvin.settings import Settings
from pydantic_settings import SettingsConfigDict

pytest.skip("TODO: Solidify settings tests", allow_module_level=True)


@pytest.fixture
def temp_env_file():
    with NamedTemporaryFile("w", delete=False) as temp_file:
        temp_file_path = Path(temp_file.name)
    yield temp_file_path
    temp_file_path.unlink()


def test_api_key_initialization_from_temp_env(temp_env_file):
    test_api_key = "test_api_key_123"
    with open(temp_env_file, "w") as file:
        file.write(f"MARVIN_OPENAI_API_KEY={test_api_key}")

    temp_model_config = SettingsConfigDict(env_prefix="marvin_", env_file=temp_env_file)
    settings = Settings(model_config=temp_model_config)

    assert settings.openai.api_key.get_secret_value() == test_api_key


def test_runtime_api_key_override(temp_env_file):
    override_api_key = "override_api_key_456"
    with open(temp_env_file, "w") as file:
        file.write(f"MARVIN_OPENAI_API_KEY={override_api_key}")

    temp_model_config = SettingsConfigDict(env_prefix="marvin_", env_file=temp_env_file)
    settings = Settings(model_config=temp_model_config)

    assert settings.openai.api_key.get_secret_value() == override_api_key
