import sys
import typer
from rich.console import Console
from typing import Optional
from marvin.client.openai import AsyncMarvinClient
from marvin.types import StreamingChatResponse
from marvin.utilities.asyncio import run_sync
from marvin.utilities.openai import get_openai_client
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
        run_sync(stdin_chat(model, max_tokens))
    else:
        console.print(ctx.get_help())


async def stdin_chat(model: str, max_tokens: int):
    client = get_openai_client()
    content = sys.stdin.read()

    client = AsyncMarvinClient()
    await client.generate_chat(
        model=model,
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens,
        stream=True,
        stream_callback=print_chunk,
    )


def print_chunk(streaming_response: StreamingChatResponse):
    last_chunk_flag = False
    text_chunk = streaming_response.chunk.choices[0].delta.content or ""
    if text_chunk:
        if last_chunk_flag and text_chunk.startswith(" "):
            text_chunk = text_chunk[1:]
        sys.stdout.write(text_chunk)
        sys.stdout.flush()
        last_chunk_flag = text_chunk.endswith(" ")


if __name__ == "__main__":
    app()
