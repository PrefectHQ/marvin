import sys
import typer
from rich.console import Console
from typing import Optional

from marvin.utilities.asyncio import run_sync
from marvin.cli.chat import chat, stdin_chat
from marvin.cli.version import display_version

app = typer.Typer()
console = Console()

app.command(name="chat")(chat)
app.command(name="version")(display_version)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    model: Optional[str] = typer.Option("gpt-3.5-turbo"),
    max_tokens: Optional[int] = typer.Option(1000),
):
    if ctx.invoked_subcommand is not None:
        return
    elif ctx.invoked_subcommand is None and not sys.stdin.isatty():
        run_sync(stdin_chat(model, max_tokens))
    else:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
