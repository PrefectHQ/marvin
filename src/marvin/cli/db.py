import asyncio

import typer

import marvin

database_app = typer.Typer(help="Database commands")


@database_app.command()
def create(
    confirm: bool = typer.Option(
        False,
        prompt="Are you sure you want to create the database?",
        help="Confirm before creating the database.",
    )
):
    if confirm:
        asyncio.run(marvin.infra.db.create_db())
    else:
        typer.echo("Database creation cancelled.")


@database_app.command()
def destroy(
    confirm: bool = typer.Option(
        False,
        prompt="Are you sure you want to destroy the database?",
        help="Confirm before destroying the database.",
    )
):
    if confirm:
        asyncio.run(marvin.infra.db.destroy_db())
    else:
        typer.echo("Database destruction cancelled.")


@database_app.command()
def reset(
    confirm: bool = typer.Option(
        False,
        prompt="Are you sure you want to reset the database?",
        help="Confirm before resetting the database.",
    )
):
    if confirm:
        asyncio.run(marvin.infra.db.reset_db())
    else:
        typer.echo("Reset cancelled.")
