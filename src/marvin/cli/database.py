import asyncio

import alembic
import typer
from rich import print

import marvin

database_app = typer.Typer(help="Database commands")


@database_app.command()
def create(
    confirm: bool = typer.Option(
        False,
        "-y",
        prompt="Are you sure you want to create the database?",
        help="Confirm before creating the database.",
    )
):
    if confirm:
        marvin.infra.database.alembic_upgrade()
    else:
        print("[red]Database creation cancelled.[/]")


@database_app.command()
def upgrade(
    confirm: bool = typer.Option(
        False,
        "-y",
        prompt="Are you sure you want to upgrade the database?",
        help="Confirm before creating the database.",
    )
):
    """Upgrade the database."""
    if confirm:
        marvin.infra.database.alembic_upgrade()
    else:
        print("[red]Database upgrade cancelled.[/]")


@database_app.command()
def downgrade(
    revision: str = typer.Option(
        "base", "--revision", "-r", help="Revision to downgrade to"
    ),
    confirm: bool = typer.Option(
        False,
        "-y",
        prompt="Are you sure you want to downgrade the database?",
        help="Confirm before creating the database.",
    ),
):
    """Downgrade the database."""
    if confirm:
        marvin.infra.database.alembic_downgrade(revision=revision)
    else:
        print("[red]Database upgrade cancelled.[/]")


@database_app.command()
def destroy(
    confirm: bool = typer.Option(
        False,
        "-y",
        prompt="Are you sure you want to destroy the database?",
        help="Confirm before destroying the database.",
    )
):
    if confirm:
        asyncio.run(marvin.infra.database.destroy_db(confirm=confirm))
    else:
        print("[red]Database destruction cancelled.[/]")


@database_app.command()
def reset(
    confirm: bool = typer.Option(
        False,
        "-y",
        prompt="Are you sure you want to reset the database?",
        help="Confirm before resetting the database.",
    )
):
    if confirm:
        asyncio.run(marvin.infra.database.reset_db(confirm=confirm))
    else:
        print("[red]Reset cancelled.[/]")


@database_app.command()
def revision(
    message: str = typer.Argument(..., help="Revision message"),
    no_autogenerate: bool = typer.Option(
        False, "--no-autogenerate", help="Do not autogenerate revision"
    ),
    rev_id: str = typer.Option(
        None, "--revision-id", help="Specify a revision id instead of generating one"
    ),
):
    autogenerate = not no_autogenerate
    alembic_cfg = marvin.infra.database._alembic_cfg()
    alembic.command.revision(
        alembic_cfg, message=message, autogenerate=autogenerate, rev_id=rev_id
    )
    print("[green]Revision created.[/]")
