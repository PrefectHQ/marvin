import os

import pytest

from marvin.settings import Settings


@pytest.fixture
def current_user() -> str:
    user = os.getenv("USER")
    assert user is not None, "USER environment variable must be set"
    return user


def test_database_url_default(current_user: str):
    settings = Settings()
    assert settings.database_url == f"/Users/{current_user}/.marvin/marvin.db"


@pytest.mark.parametrize(
    "env_var_value, expected_database_url",
    [
        (":memory:", ":memory:"),
        ("~/.marvin/test.db", "/Users/{user}/.marvin/test.db"),
    ],
)
def test_database_url_set_from_env_var(
    monkeypatch: pytest.MonkeyPatch,
    env_var_value: str,
    expected_database_url: str,
    current_user: str,
):
    monkeypatch.setenv("MARVIN_DATABASE_URL", env_var_value)
    settings = Settings()
    assert settings.database_url == expected_database_url.format(user=current_user)
