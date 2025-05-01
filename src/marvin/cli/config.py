import typer
from rich import print

import marvin

config_app = typer.Typer(
    name="config", help="Manage Marvin configuration.", no_args_is_help=True
)


@config_app.command()
def view():
    """Display the current Marvin settings."""
    print(marvin.settings)


@config_app.command()
def get(key: str):
    """Get the value of a specific setting."""
    try:
        value = getattr(marvin.settings, key.lower())
        print(f"{key}: {value}")
    except AttributeError:
        print(f"Error: Setting '{key}' not found.")
        raise typer.Exit(1)
