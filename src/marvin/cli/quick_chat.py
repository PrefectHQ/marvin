import asyncio
import random

import typer
from rich import print
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

    print(f"[bold blue]:robot: {bot.name}[/] is ready!")
    print("[italic](Type `exit` to quit)[/]")

    try:
        while True:
            if not first_message:
                message = Prompt.ask("\n[green]Your message[/]")
            else:
                message = first_message
                first_message = None
                print(f"\n[green]Your message[/]: {message}")

            if message == "exit":
                raise KeyboardInterrupt()

            # empty print so the progress and response appear on the same line
            print()
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(
                    description=random.choice(spinner_messages), total=None
                )
                response = await bot.say(message)

            print(f"[blue]{bot.name}:[/] {response.content}")
            if single_response:
                raise typer.Exit()

    except KeyboardInterrupt:
        print("\n[red]:wave: Goodbye![/]")


@app.command(name="chat", help="Quickly chat with a custom bot")
def chat_sync(
    message: str = typer.Argument(
        default=None, help="An optional initial message to send to the bot"
    ),
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
):
    if single_response and not message:
        raise typer.BadParameter("You must provide a message to get a single response.")
    asyncio.run(
        chat(
            first_message=message,
            name=name,
            personality=personality,
            instructions=instructions,
            single_response=single_response,
        )
    )
