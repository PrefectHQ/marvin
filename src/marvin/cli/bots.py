import asyncio

import typer
from fastapi import HTTPException
from rich import print
from rich.table import Table

import marvin
from marvin.bots.base import DEFAULT_INSTRUCTIONS, DEFAULT_PERSONALITY
from marvin.utilities.strings import condense_newlines

bots_app = typer.Typer(help="Bot commands")


@bots_app.command()
def ls():
    async def _ls() -> list[marvin.models.bots.BotConfig]:
        return await marvin.api.bots.get_bot_configs()

    bot_configs = asyncio.run(_ls())

    table = Table(
        title="Bot Configs",
        row_styles=["", "dim"],
        header_style="bold blue",
        leading=1,
    )
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Personality")
    table.add_column("Instructions")

    for bot in bot_configs:
        if condense_newlines(bot.personality) == condense_newlines(DEFAULT_PERSONALITY):
            personality = "(default)"
        else:
            personality = bot.personality

        if condense_newlines(bot.instructions) == condense_newlines(
            DEFAULT_INSTRUCTIONS
        ):
            instructions = "(default)"
        else:
            instructions = bot.instructions

        table.add_row(bot.name, bot.description, personality, instructions)

    print(table)


@bots_app.command()
def create(
    name: str = typer.Argument(...),
    description: str = typer.Option(
        None, "--description", "-d", help="The description to use for this bot"
    ),
    personality: str = typer.Option(
        None, "--personality", "-p", help="The personality to use for this bot"
    ),
    instructions: str = typer.Option(
        None, "--instructions", "-i", help="The instructions to use for this bot"
    ),
):
    async def _create():
        kwargs = {}
        if description is not None:
            kwargs["description"] = description
        if personality is not None:
            kwargs["personality"] = personality
        if instructions is not None:
            kwargs["instructions"] = instructions
        try:
            await marvin.api.bots.create_bot_config(
                marvin.models.bots.BotConfigCreate(name=name, **kwargs)
            )
        except HTTPException as exc:
            if exc.status_code == 409:
                print(f'[red]Bot config "{name}" already exists![/]')
                raise typer.Exit(1)
            raise

    asyncio.run(_create())
    print(f'[green]Bot config "{name}" created![/]')


@bots_app.command()
def update(
    name: str = typer.Argument(...),
    description: str = typer.Option(
        None, "--description", "-d", help="The description to use for this bot"
    ),
    personality: str = typer.Option(
        None, "--personality", "-p", help="The personality to use for this bot"
    ),
    instructions: str = typer.Option(
        None, "--instructions", "-i", help="The instructions to use for this bot"
    ),
):
    async def _create():
        kwargs = {}
        if description is not None:
            kwargs["description"] = description
        if personality is not None:
            kwargs["personality"] = personality
        if instructions is not None:
            kwargs["instructions"] = instructions
        await marvin.api.bots.update_bot_config(
            name=name,
            bot_config=marvin.models.bots.BotConfigUpdate(**kwargs),
        )

    asyncio.run(_create())
    print(f'[green]Bot config "{name}" updated![/]')


@bots_app.command()
def delete(name: str = typer.Argument(...)):
    async def _delete():
        await marvin.api.bots.delete_bot_config(name)

    asyncio.run(_delete())
    print(f'[green]Bot config "{name}" deleted![/]')
