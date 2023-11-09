import sys
import typer
from rich.console import Console
from typing import Optional
from marvin.utilities.asyncutils import run_sync
from marvin.utilities.openai import get_client
from marvin.cli.version import display_version

app = typer.Typer()
console = Console()

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
        run_sync(process_stdin(model, max_tokens))
    else:
        console.print(ctx.get_help())


async def process_stdin(model: str, max_tokens: int):
    client = get_client()
    content = sys.stdin.read()
    last_chunk_ended_with_space = False

    async for part in await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens,
        stream=True,
    ):
        print_chunk(part, last_chunk_ended_with_space)


def print_chunk(part, last_chunk_flag):
    text_chunk = part.choices[0].delta.content or ""
    if text_chunk:
        if last_chunk_flag and text_chunk.startswith(" "):
            text_chunk = text_chunk[1:]
        sys.stdout.write(text_chunk)
        sys.stdout.flush()
        last_chunk_flag = text_chunk.endswith(" ")


if __name__ == "__main__":
    app()
