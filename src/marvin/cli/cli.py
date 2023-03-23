import asyncio

import dotenv
import typer
from rich import print as rprint
from rich.prompt import Prompt

import marvin

from .db import database_app
from .server import server_app

app = typer.Typer()
app.add_typer(database_app, name="database")
app.add_typer(server_app, name="server")


@app.command(name="setup-openai", help="Set up OpenAI")
def setup_openai():
    from marvin.config import ENV_FILE

    if not marvin.settings.openai_api_key.get_secret_value():
        rprint(
            "\n[red bold]No OpenAI API key found![/] Please visit "
            " https://beta.openai.com/account/api-keys to create one."
        )

        rprint(
            "\nYou can store"
            " your API key as either [gray50]`OPENAI_API_KEY`[/] or"
            " [gray50]`MARVIN_OPENAI_API_KEY`[/] in your environment, or you can enter"
            " it here to save it in your Marvin configuration. You can run"
            " [gray50]`marvin setup-openai`[/] to view this screen again. \n"
        )

    api_key = Prompt.ask(
        (
            f"Enter your OpenAI API key to save it to [italic gray50]{ENV_FILE}[/], or"
            " hit enter to unset"
        ),
        password=True,
    )
    if api_key:
        marvin.settings.openai_api_key = api_key
        dotenv.set_key(str(ENV_FILE), "MARVIN_OPENAI_API_KEY", api_key)
        rprint("API key set!")
    else:
        marvin.settings.openai_api_key = ""
        dotenv.set_key(str(ENV_FILE), "MARVIN_OPENAI_API_KEY", "")
        rprint("API key unset!")


@app.command(name="chat", help="Quickly chat with a custom bot")
def chat(
    name: str = typer.Option(None, "--name", "-n", help="Your bot's name"),
    personality: str = typer.Option(
        None, "--personality", "-p", help="Your bot's personality"
    ),
    instructions: str = typer.Option(
        None, "--instructions", "-i", help="Your bot's instructions"
    ),
    message: list[str] = typer.Argument(
        default=None, help="An optional initial message to send to the bot"
    ),
):
    if not marvin.settings.openai_api_key.get_secret_value():
        setup_openai()

    bot = marvin.Bot(name=name, personality=personality, instructions=instructions)
    asyncio.run(bot.interactive_chat(first_message=" ".join(message)))


if __name__ == "__main__":
    app()
