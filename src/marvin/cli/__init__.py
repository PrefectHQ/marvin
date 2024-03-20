import sys
import typer
from rich.console import Console
from typing import Optional
from marvin.client.openai import AsyncMarvinClient
from marvin.types import StreamingChatResponse
from marvin.utilities.asyncio import run_sync
from marvin.utilities.openai import get_openai_client
from marvin.beta.assistants import Assistant
from marvin.cli.threads import threads_app
from marvin.cli.assistants import assistants_app, say as assistants_say

import platform

from typer import Context, Exit, echo

from marvin import __version__

app = typer.Typer(no_args_is_help=True)
console = Console()
app.add_typer(threads_app, name="thread")
app.add_typer(assistants_app, name="assistant")
app.command(name="say")(assistants_say)


@app.command()
def version(ctx: Context):
    if ctx.resilient_parsing:
        return
    echo(f"Version:\t\t{__version__}")
    echo(f"Python version:\t\t{platform.python_version()}")
    echo(f"OS/Arch:\t\t{platform.system().lower()}/{platform.machine().lower()}")
    raise Exit()


if __name__ == "__main__":
    app()
