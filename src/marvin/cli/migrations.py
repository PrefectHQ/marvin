"""Command line utilities for database migrations."""

import asyncio
import os
import sys

import typer
from rich.console import Console
from rich.table import Table

from marvin.database import (
    ALEMBIC_DIR,
    ALEMBIC_INI,
    get_async_engine,
    is_sqlite,
)
from marvin.utilities.logging import get_logger

logger = get_logger(__name__)
console = Console()

# Create a Typer app for user-facing migration commands
migrations = typer.Typer(
    name="db", help="Manage database migrations.", no_args_is_help=True
)

# Create a Typer app for developer migration commands
migrations_dev = typer.Typer(
    help="Developer database migration commands.", no_args_is_help=True
)


def get_alembic_cfg():
    """Get the Alembic config."""
    from alembic.config import Config

    cfg = Config(str(ALEMBIC_INI))
    return cfg


async def _run_revision_with_connection(connection, alembic_cfg, message, autogenerate):
    """Run revision command with async connection."""
    from alembic import command

    def do_revision(connection):
        alembic_cfg.attributes["connection"] = connection
        command.revision(alembic_cfg, message=message, autogenerate=autogenerate)

    await connection.run_sync(do_revision)


@migrations_dev.command("revision")
def revision(
    autogenerate: bool = typer.Option(
        False,
        "--autogenerate/--no-autogenerate",
        help="Automatically generate migrations based on schema changes",
    ),
    message: str = typer.Option(None, "--message", "-m", help="Migration message"),
):
    """Create a new migration revision. Developer command."""
    try:
        # Ensure versions directory exists
        versions_dir = ALEMBIC_DIR / "versions"
        os.makedirs(versions_dir, exist_ok=True)

        alembic_cfg = get_alembic_cfg()

        from alembic import command

        command.revision(alembic_cfg, message=message, autogenerate=autogenerate)
        console.print("[green]Migration revision created[/green]")
        return

    except Exception as e:
        console.print(f"[red]Failed to create migration revision: {e}[/red]")
        sys.exit(1)


@migrations.command("upgrade")
def upgrade(
    revision: str = typer.Argument(
        "head", help="Revision to upgrade to. Use 'head' for latest."
    ),
):
    """Upgrade database to the latest migration."""
    try:
        from alembic import command

        # Ensure versions directory exists
        versions_dir = ALEMBIC_DIR / "versions"
        os.makedirs(versions_dir, exist_ok=True)

        alembic_cfg = get_alembic_cfg()
        command.upgrade(alembic_cfg, revision)
        console.print(f"[green]Database upgraded to {revision}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to upgrade database: {e}[/red]")
        sys.exit(1)


@migrations.command("downgrade")
def downgrade(
    revision: str = typer.Argument(..., help="Revision to downgrade to"),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Confirm the destructive operation without prompting"
    ),
):
    """Downgrade database to specified revision. Requires confirmation."""
    if not yes:
        confirmation = typer.confirm(
            f"WARNING: You are about to downgrade the database to revision '{revision}'. "
            f"This operation is destructive and may result in data loss. Continue?",
            default=False,
        )
        if not confirmation:
            console.print("[yellow]Operation cancelled.[/yellow]")
            sys.exit(0)

    try:
        from alembic import command

        alembic_cfg = get_alembic_cfg()
        command.downgrade(alembic_cfg, revision)
        console.print(f"[green]Database downgraded to {revision}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to downgrade database: {e}[/red]")
        sys.exit(1)


@migrations.command("reset")
def reset(
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Confirm the destructive operation without prompting"
    ),
):
    """Reset database by downgrading to base and upgrading to head. Requires confirmation."""
    if not yes:
        confirmation = typer.confirm(
            "WARNING: You are about to reset the database to the latest migration. "
            "This operation is destructive and may result in data loss. Continue?",
            default=False,
        )
        if not confirmation:
            console.print("[yellow]Operation cancelled.[/yellow]")
            sys.exit(0)

    try:
        from alembic import command

        alembic_cfg = get_alembic_cfg()

        # Downgrade to base (before first migration)
        console.print("[blue]Downgrading database to base state...[/blue]")
        command.downgrade(alembic_cfg, "base")

        # Upgrade to latest
        console.print("[blue]Upgrading database to latest migration...[/blue]")
        command.upgrade(alembic_cfg, "head")

        console.print("[green]Database reset complete[/green]")
    except Exception as e:
        console.print(f"[red]Failed to reset database: {e}[/red]")
        sys.exit(1)


@migrations.command("history")
def history():
    """Show migration history."""
    try:
        from alembic import command

        alembic_cfg = get_alembic_cfg()
        command.history(alembic_cfg)
    except Exception as e:
        console.print(f"[red]Failed to show migration history: {e}[/red]")
        sys.exit(1)


@migrations.command("current")
def current():
    """Show current migration revision."""
    try:
        from alembic import command

        alembic_cfg = get_alembic_cfg()
        command.current(alembic_cfg)
    except Exception as e:
        console.print(f"[red]Failed to show current migration: {e}[/red]")
        sys.exit(1)


async def _get_migration_status(connection, alembic_cfg, script):
    """Get migration status using async connection."""
    from alembic.runtime.migration import MigrationContext

    def get_current_rev(connection):
        context = MigrationContext.configure(connection)
        return context.get_current_revision()

    return await connection.run_sync(get_current_rev)


@migrations.command("init")
def init_db():
    """Create database tables directly without using migrations."""
    try:
        from marvin.database import create_db_and_tables

        console.print("[blue]Creating database tables...[/blue]")
        asyncio.run(create_db_and_tables())
        console.print("[green]Database tables created successfully[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create database tables: {e}[/red]")
        sys.exit(1)


@migrations.command("status")
def status():
    """Show database migration status and information."""
    from marvin.settings import settings

    is_sqlite_db = is_sqlite()
    db_url = settings.database_url or "Not configured"

    # Format sensitive parts of the URL for display
    if db_url != "Not configured":
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(db_url)

        # For better security, create a sanitized URL that masks credentials
        # but preserves the database type, host, port, and database name
        if parsed.netloc and "@" in parsed.netloc:
            # Extract the host:port part after the @ symbol
            host_part = parsed.netloc.split("@")[1]
            # Create a netloc with masked credentials
            masked_netloc = f"****:****@{host_part}"

            # Reconstruct URL with masked credentials
            sanitized_parts = list(parsed)
            sanitized_parts[1] = masked_netloc  # Replace netloc
            display_url = urlunparse(sanitized_parts)
        else:
            # For SQLite or URLs without credentials, use as is
            display_url = db_url
    else:
        display_url = db_url

    # Use a borderless table for config
    config_table = Table.grid(padding=(0, 2))
    config_table.add_column(style="bold")
    config_table.add_column()

    console.print("[bold]DATABASE CONFIGURATION[/bold]")
    config_table.add_row("Database URL:", display_url)
    config_table.add_row(
        "Database Type:", "SQLite" if is_sqlite_db else "PostgreSQL/Other"
    )
    console.print(config_table)
    console.print()

    # Check migration status
    try:
        from alembic.script import ScriptDirectory

        # Ensure versions directory exists
        versions_dir = ALEMBIC_DIR / "versions"
        os.makedirs(versions_dir, exist_ok=True)

        alembic_cfg = get_alembic_cfg()
        script = ScriptDirectory.from_config(alembic_cfg)

        # Get head revision
        head_revision = script.get_current_head()

        # Get current revision using async engine
        async def get_async_status():
            engine = get_async_engine()
            async with engine.connect() as connection:
                current_revision = await _get_migration_status(
                    connection, alembic_cfg, script
                )
            await engine.dispose()
            return current_revision

        current_revision = asyncio.run(get_async_status())

        # Use a borderless table for migration status
        migration_table = Table.grid(padding=(0, 2))
        migration_table.add_column(style="bold")
        migration_table.add_column()

        console.print("[bold]MIGRATION STATUS[/bold]")

        # Show current revision
        current_rev_display = (
            current_revision
            if current_revision
            else "[red]Not set (no migrations applied)[/red]"
        )
        migration_table.add_row("Current Revision:", current_rev_display)

        # Show head revision
        head_rev_display = head_revision if head_revision else "No migrations found"
        migration_table.add_row("Head Revision:", head_rev_display)

        # Determine migration status
        status_text = ""
        status_style = "green"

        if not head_revision:
            status_text = "No migrations exist yet"
            status_style = "yellow"
        elif not current_revision:
            status_text = "Database has no migrations applied but migrations exist"
            status_style = "red"
        elif current_revision == head_revision:
            status_text = "Database is up to date"
            status_style = "green"
        else:
            # Calculate how many revisions behind
            revs = list(script.iterate_revisions(head_revision, current_revision))
            migration_count = len(revs)
            status_text = f"Database is behind by {migration_count} migration{'s' if migration_count > 1 else ''}"
            status_style = "yellow"

        migration_table.add_row(
            "Status:", f"[{status_style}]{status_text}[/{status_style}]"
        )
        console.print(migration_table)

        # Show upgrade message if needed
        if status_style == "yellow" and current_revision != head_revision:
            console.print()
            console.print(
                "[yellow]Run 'marvin db upgrade' to apply pending migrations[/yellow]"
            )

    except Exception as e:
        console.print(f"[yellow]Could not determine migration status: {e}[/yellow]")
        if "No such revision" in str(e):
            console.print(
                "Run 'marvin dev db revision -m \"initial\"' to create an initial migration"
            )
