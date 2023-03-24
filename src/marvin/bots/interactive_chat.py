import random

from rich import print as rprint
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from marvin.bots.base import Bot

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
    "Combing the hair of multiple alpacas...",
    "Re-evaulating my life choices...",
    "Copying things from Stack Overflow...",
]


async def chat(bot: Bot, first_message: str = None):
    rprint(f"\n[bold blue]:robot::speech_balloon: {bot.name}[/] is listening...\n")

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
                Panel(
                    message,
                    title="You",
                    title_align="left",
                    border_style="gray50",
                )
            )

            if message == "exit":
                raise KeyboardInterrupt()
            elif message == "!forget":
                await bot.reset_thread()
                rprint(
                    Panel(
                        (
                            "**Dazed and confused** :robot_face: Where am I? What's"
                            " going on?"
                        ),
                        title=bot.name,
                        title_align="left",
                        border_style="blue",
                    )
                )
                continue

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

    except KeyboardInterrupt:
        rprint()
        rprint(Panel(":wave: Goodbye!", border_style="red"))
