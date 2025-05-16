import os

import pytest

from marvin.settings import Settings


def test_database_url_default(monkeypatch: pytest.MonkeyPatch):
    # Ensure MARVIN_DATABASE_URL is not set for this specific test
    # to allow the true default logic in Settings to apply.
    monkeypatch.delenv("MARVIN_DATABASE_URL", raising=False)

    settings = Settings()
    assert settings.database_url is not None
    assert settings.database_url.endswith("/.marvin/marvin.db")


@pytest.mark.parametrize(
    "env_var_value, expected",
    [
        (
            "sqlite+aiosqlite:///" + os.path.expanduser("~/.marvin/test.db"),
            "sqlite+aiosqlite:///" + os.path.expanduser("~/.marvin/test.db"),
        ),
        (
            "postgresql+asyncpg://user:password@host:port/database",
            "postgresql+asyncpg://user:password@host:port/database",
        ),
    ],
)
def test_database_url_set_from_env_var(
    monkeypatch: pytest.MonkeyPatch,
    env_var_value: str,
    expected: str,
):
    monkeypatch.setenv("MARVIN_DATABASE_URL", env_var_value)
    settings = Settings()
    assert settings.database_url == expected


def test_database_url_ignores_unprefixed_env_var_uses_default(
    monkeypatch: pytest.MonkeyPatch,
):
    """Test that an unprefixed DATABASE_URL is ignored if MARVIN_DATABASE_URL is not set."""
    monkeypatch.delenv("MARVIN_DATABASE_URL", raising=False)
    ignored_value = "ignored_db_url_for_test"
    monkeypatch.setenv("DATABASE_URL", ignored_value)

    settings = Settings()

    assert settings.database_url is not None
    # Check that it falls back to the default path
    assert settings.database_url.endswith("/.marvin/marvin.db")
    # Ensure it did not pick up the unprefixed DATABASE_URL
    assert settings.database_url != ignored_value
