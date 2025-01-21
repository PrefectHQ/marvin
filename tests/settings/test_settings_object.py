import pytest

from marvin.settings import Settings


def test_database_url_default():
    settings = Settings()
    assert settings.database_url is not None
    assert settings.database_url.endswith("/.marvin/marvin.db")


@pytest.mark.parametrize(
    "env_var_value, expected_ending",
    [
        (":memory:", ":memory:"),
        ("~/.marvin/test.db", "/.marvin/test.db"),
    ],
)
def test_database_url_set_from_env_var(
    monkeypatch: pytest.MonkeyPatch,
    env_var_value: str,
    expected_ending: str,
):
    monkeypatch.setenv("MARVIN_DATABASE_URL", env_var_value)
    settings = Settings()
    if expected_ending == ":memory:":
        assert settings.database_url == expected_ending
    else:
        assert settings.database_url is not None
        assert settings.database_url.endswith(expected_ending)