import asyncio
import random

import typer
from rich import print as rprint
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

import marvin

from .cli import app

spinner_messages = [
    "Thinking...",
    "Processing...",
    "Beep boop, definitely not a bot...",
    "Doing AI things...",
    "Loading bot.exe...",
    "Solving for x...",
    "Catching up on the news...",
    "Brewing coffee...",
    "Consulting my magic 8-bit ball...",
    "Artificial neurons firing...",
    "Checking my sources...",
    "Summoning digital spirits...",
    "Channeling HAL...",
    "Juggling 1s and 0s...",
    "Mining the data...",
    "Engaging neural nets...",
    "Whispering to algorithms...",
    "Crunching the data...",
    "Orchestrating...",
    "Diving into the matrix...",
    "Channeling my inner Turing...",
    "Connecting the digital dots...",
    "Gathering bits and bytes...",
    "Going with the dataflow...",
    "Tapping into the data stream...",
    "Calling a friend...",
    "Using a lifeline...",
    "Dusting off my personality...",
]


async def chat(
    first_message: str = None,
    name: str = None,
    personality: str = None,
    instructions: str = None,
    single_response: bool = False,
):
    bot = marvin.Bot(name=name, personality=personality, instructions=instructions)

    rprint(f"\n[bold blue]:robot::speech_balloon: {bot.name}[/] is ready!\n")

    try:
        while True:
            if not first_message:
                message = Prompt.ask("\n[gray50]Your message[/]")
                # this will clear the prompt off the screen
                print("\033[A\033[A")
            else:
                message = first_message
                first_message = None
            rprint(
                Panel(message, title="You", title_align="left", border_style="gray50")
            )

            if message == "exit":
                raise KeyboardInterrupt()

            # empty rprint so the progress and response appear on the same line
            rprint()
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(
                    description=random.choice(spinner_messages), total=None
                )
                response = await bot.say(message)

            rprint(
                Panel(
                    response.content,
                    title=bot.name,
                    title_align="left",
                    border_style="blue",
                )
            )
            if single_response:
                raise typer.Exit()

    except KeyboardInterrupt:
        rprint()
        rprint(Panel(":wave: Goodbye!", border_style="red"))


@app.command(name="chat", help="Quickly chat with a custom bot")
def chat_sync(
    name: str = typer.Option(None, "--name", "-n", help="Your bot's name"),
    personality: str = typer.Option(
        None, "--personality", "-p", help="Your bot's personality"
    ),
    instructions: str = typer.Option(
        None, "--instructions", "-i", help="Your bot's instructions"
    ),
    single_response: bool = typer.Option(
        False, "--single-response", help="Get a single response and exit"
    ),
    message: list[str] = typer.Argument(
        default=None, help="An optional initial message to send to the bot"
    ),
):
    if single_response and not message:
        raise typer.BadParameter("You must provide a message to get a single response.")
    asyncio.run(
        chat(
            first_message=" ".join(message),
            name=name,
            personality=personality,
            instructions=instructions,
            single_response=single_response,
        )
    )
