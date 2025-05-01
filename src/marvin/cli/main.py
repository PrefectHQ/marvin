import logging
import platform
import sys
from functools import partial
from pathlib import Path

import pydantic_ai
import typer
from pydantic_core import to_json
from rich.console import Console
from rich.table import Table
from typer import Context, Exit

import marvin

from .config import config_app
from .dev import dev_app
from .migrations import migrations as migrations_app
from .migrations import migrations_dev

console = Console()

app = typer.Typer(no_args_is_help=True)

# Add the migrations commands to the dev app
dev_app.add_typer(migrations_dev, name="db")

# Add the main app commands
app.add_typer(dev_app, name="dev")
app.add_typer(migrations_app, name="db")
app.add_typer(config_app, name="config")
logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)


@app.command()
def version(ctx: Context):
    if ctx.resilient_parsing:
        return

    info = {
        "Marvin version": marvin.__version__,
        "Pydantic AI version": pydantic_ai.__version__,
        "Python version": platform.python_version(),
        "Platform": platform.platform(),
        "Path": f"~/{Path(__file__).resolve().parents[3].relative_to(Path.home())}",
    }

    g = Table.grid(padding=(0, 1))
    g.add_column(style="bold", justify="left")
    g.add_column(style="cyan", justify="right")
    for k, v in info.items():
        g.add_row(k + ":", str(v).replace("\n", " "))
    console.print(g)

    raise Exit()


@app.command()
def x(
    operation: str = typer.Option(
        "extract", "--operation", "-o", help="Operation to perform"
    ),
    target_type: str = typer.Option(
        "str",
        "--type",
        "-t",
        help="Type of entities to extract (any type that can be eval'd)",
    ),
    instructions: str = typer.Option(
        None, "--instructions", "-i", help="Instructions for extraction"
    ),
    n: int = typer.Option(1, "--n", "-n", help="Number of results to generate"),
):
    """
    Extract entities from stdin input.

    Example: echo "one, two, three" | marvin x -t int | jq
    """
    from marvin.settings import settings

    operation_fn = getattr(marvin, operation)
    if n != 1 and operation != "generate":
        raise ValueError("can only specify n for 'generate' operation")

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
        if operation == "extract":
            operation_fn = partial(
                operation_fn, data=data, target=target_type, instructions=instructions
            )
        elif operation == "cast":
            operation_fn = partial(operation_fn, data=data, target=target_type)
        elif operation == "generate":
            operation_fn = partial(
                operation_fn,
                target=target_type,
                n=n,
                instructions=f"use this as context: {data}",
            )
        print(to_json(operation_fn()).decode("utf-8"))
    except AttributeError:
        print(f"Error: Unsupported operation '{operation}'", file=sys.stderr)
        sys.exit(1)
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
