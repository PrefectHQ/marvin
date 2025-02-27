import logging
import platform
import sys
from pathlib import Path

import pydantic_ai
import typer
from pydantic_core import to_json
from rich.console import Console
from rich.table import Table
from typer import Context, Exit

from marvin import __version__
from marvin.fns.extract import extract as marvin_extract

from .dev import dev_app

console = Console()

app = typer.Typer(no_args_is_help=True)

app.add_typer(dev_app, name="dev")
logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)


@app.command()
def version(ctx: Context):
    if ctx.resilient_parsing:
        return

    info = {
        "Marvin version": __version__,
        "Pydantic AI version": pydantic_ai.__version__,
        "Python version": platform.python_version(),
        "Platform": platform.platform(),
        "Path": Path(__file__).resolve().parents[3],
    }

    g = Table.grid(padding=(0, 1))
    g.add_column(justify="right")
    g.add_column()
    for k, v in info.items():
        g.add_row(k + ":", str(v).replace("\n", " "))
    console.print(g)

    raise Exit()


@app.command()
def extract(
    target_type: str = typer.Option(
        "str", "--type", "-t", help="Type of entities to extract (str, int, float)"
    ),
    instructions: str = typer.Option(
        None, "--instructions", "-i", help="Instructions for extraction"
    ),
):
    """
    Extract entities from stdin input.

    Example: echo "one, two, three" | marvin extract -t int | jq
    """
    from marvin.settings import settings

    # Read from stdin if available
    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
    else:
        print("Error: No input provided via stdin", file=sys.stderr)
        sys.exit(1)

    try:
        target_type = eval(target_type)
    except Exception:
        print(f"Error: Unsupported type '{target_type}'", file=sys.stderr)
        sys.exit(1)

    if settings.log_level == "DEBUG":
        raise Exception(
            "This can't be run with DEBUG logging, preface this command with MARVIN_LOG_LEVEL=CRITICAL"
        )

    try:
        result = marvin_extract(data, target_type, instructions=instructions)
        print(to_json(result).decode("utf-8"))
    except Exception as e:
        print(f"Error during extraction: {e}", file=sys.stderr)
        sys.exit(1)


# this callback only exists to force `version` to be called as `marvin
# version` instead of as the default command, which is the default behavior when
# there's only one command. It can be deleted if/when more commands are added.
@app.callback()
def callback():
    pass


if __name__ == "__main__":
    app()
