import asyncio

import typer
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

import marvin


async def main():
    bot = marvin.Bot()

    print(f"[bold green]:robot: {bot.name} is ready![/]")

    try:
        while True:
            message = Prompt.ask("Your message")

            if message == "exit":
                raise KeyboardInterrupt()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Processing...", total=None)
                response = await bot.say(message)

            print(f"[blue]{bot.name}:[/blue] {response}")
    except KeyboardInterrupt:
        print("\n[red]:wave: Goodbye![/red]")


def main_sync():
    asyncio.run(main())


if __name__ == "__main__":
    typer.run(main_sync)
