import asyncio

import typer
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

import marvin

app = typer.Typer()


async def chat(name: str, personality: str):
    bot = marvin.Bot(name=name, personality=personality)

    print(f"[bold blue]:robot: {bot.name} is listening![/]")

    try:
        while True:
            message = Prompt.ask("\n[green]Your message[/]")

            if message == "exit":
                raise KeyboardInterrupt()

            print()
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Thinking...", total=None)
                response = await bot.say(message)

            print(f"[blue]{bot.name}:[/] {response}")
    except KeyboardInterrupt:
        print("\n[red]:wave: Goodbye![/]")


@app.command()
def main(
    name: str = typer.Option("Marvin", "--name", "-n"),
    personality: str = typer.Option(
        "The paranoid android, eager to demonstrate his abilities.",
        "--personality",
        "-p",
    ),
):
    asyncio.run(chat(name=name, personality=personality))


if __name__ == "__main__":
    app()
