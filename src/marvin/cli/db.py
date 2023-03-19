import asyncio

import typer

import marvin

database_app = typer.Typer()


@database_app.command()
def create_db():
    asyncio.run(marvin.infra.db.create_db())


@database_app.command()
def destroy_db():
    asyncio.run(marvin.infra.db.destroy_db())


@database_app.command()
def reset_db():
    asyncio.run(marvin.infra.db.reset_db())
