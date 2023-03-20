import asyncio

import typer

import marvin

from .db import database_app
from .server import server_app

app = typer.Typer()
app.add_typer(database_app, name="database")
app.add_typer(server_app, name="server")


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
    bot = marvin.Bot(name=name, personality=personality, instructions=instructions)
    asyncio.run(bot.interactive_chat(first_message=" ".join(message)))


if __name__ == "__main__":
    app()
