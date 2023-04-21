import asyncio
from importlib.metadata import version as get_version

import dotenv
import openai
import openai.error
import typer
from rich import print as rprint
from rich.prompt import Prompt

import marvin

from .bots import bots_app
from .database import database_app
from .server import server_app

app = typer.Typer()
app.add_typer(database_app, name="database")
app.add_typer(server_app, name="server")
app.add_typer(bots_app, name="bots")


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

    while True:
        api_key = Prompt.ask(
            (
                f"Enter your OpenAI API key to save it to [italic gray50]{ENV_FILE}[/],"
                " or hit enter to unset"
            ),
            password=True,
        )
        if api_key:
            # test the API key. If it's invalid, raise an error.

            try:
                openai.api_key = api_key
                # see if we can load models from the API
                openai.Model.list()
                marvin.settings.openai_api_key = api_key
                dotenv.set_key(str(ENV_FILE), "MARVIN_OPENAI_API_KEY", api_key)
                rprint("API key set!")
                raise typer.Exit()
            except openai.error.AuthenticationError:
                rprint("[red bold]Invalid API key![/] Please try again.")

        else:
            marvin.settings.openai_api_key = ""
            dotenv.set_key(str(ENV_FILE), "MARVIN_OPENAI_API_KEY", "")
            rprint("API key unset!")
            raise typer.Exit()


@app.command(name="version", help="Print the version of this package")
def version():
    print(get_version("marvin"))


@app.command(name="chat", help="Launch a TUI for chatting with all your bots.")
def chat(
    bot: str = typer.Option(
        None, "--bot", "-b", help="The name of a bot to begin chatting with"
    )
):
    from marvin.cli.tui import MarvinApp

    try:
        bot = marvin.Bot.load_sync(name=bot)
    except Exception as exc:
        marvin.get_logger().warning(exc)
        bot = None
    app = MarvinApp(default_bot=bot)
    app.run()


@app.command(name="log", help="View the logs for a bot")
def log(
    bot_name: str = typer.Argument(None, help="The name of the bot to use"),
):
    if not bot_name:
        raise ValueError("You must specify a bot to load")

    bot = asyncio.run(marvin.Bot.load(bot_name))
    rprint(asyncio.run(bot.history.log()))


if __name__ == "__main__":
    app()
