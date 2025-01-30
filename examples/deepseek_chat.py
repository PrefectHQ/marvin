import asyncio
import signal
import sys
from pathlib import Path
from typing import Any, ClassVar

import httpx
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from pydantic import Field, SecretStr
from pydantic_ai.models.openai import OpenAIModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from marvin import Agent, Thread
from marvin.settings import settings as marvin_settings

running: bool = True


def handle_sigint(signum: int, frame: Any) -> None:
    global running
    running = False


signal.signal(signal.SIGINT, handle_sigint)


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env", extra="ignore"
    )

    deepseek_api_key: SecretStr = Field(default=...)
    google_api_key: SecretStr = Field(default=...)
    google_cx: SecretStr = Field(default=...)
    notes_file_path: str = Field(default="notes.txt")


settings = Settings()


def google_search(query: str, num: int = 3) -> str:
    """Use google to search the internet.

    Args:
        query: The query to search for.
        num: The number of results to return (preferably 3)

    Returns:
        The results of the search.
    """
    response = httpx.get(
        "https://www.googleapis.com/customsearch/v1",
        params={
            "q": query,
            "key": settings.google_api_key.get_secret_value(),
            "cx": settings.google_cx.get_secret_value(),
            "num": num,
        },
    )
    response.raise_for_status()
    return response.json()


def write_to_file(content: str, file_path: str) -> None:
    """Write content to a file.

    Args:
        content: The content to write to the file
        file_path: The path to the file to write to (will be casted to a Path)
    """
    Path(file_path).write_text(content)


async def get_user_input(session: PromptSession[str]) -> str:
    try:
        return await session.prompt_async(
            "you ➤ ",
            auto_suggest=AutoSuggestFromHistory(),
        )
    except (KeyboardInterrupt, EOFError):
        global running
        running = False
        return ""


async def main(model: str | None = None) -> int:
    try:
        history_file = marvin_settings.home_path / ".deepseek-history.txt"
        session = PromptSession[str](history=FileHistory(str(history_file)))

        agent = Agent(
            name="deepseek assistant",
            model=OpenAIModel(
                model or "deepseek-chat",
                base_url="https://api.deepseek.com",
                api_key=settings.deepseek_api_key.get_secret_value(),
            ),
            tools=[google_search, write_to_file],
            prompt=f"""You are a helpful assistant that can search the internet for information.
            You can write notes in {settings.notes_file_path}.
            """,
        )

        with Thread():
            while running:
                if not (user_input := await get_user_input(session)) or not running:
                    break
                if user_input.lower() in ("exit", "quit", ":q!"):
                    break
                agent.run(user_input)
    except Exception as e:
        print(f"\nError: {e}")
        return 1
    finally:
        print("Goodbye!")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None)))
