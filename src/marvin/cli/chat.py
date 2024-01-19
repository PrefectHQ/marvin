import os
import subprocess
import sys
from collections import deque

import typer
from rich.console import Console
from rich.text import Text
from rich.theme import Theme

from marvin.client.openai import AsyncMarvinClient
from marvin.types import StreamingChatResponse

custom_theme = Theme({"info": "dim cyan", "warning": "magenta", "error": "bold red"})
console = Console(theme=custom_theme)


def print_chunk(streaming_response: StreamingChatResponse):
    last_chunk_flag = False
    text_chunk = streaming_response.chunk.choices[0].delta.content or ""
    if text_chunk:
        if last_chunk_flag and text_chunk.startswith(" "):
            text_chunk = text_chunk[1:]
        sys.stdout.write(text_chunk)
        sys.stdout.flush()
        last_chunk_flag = text_chunk.endswith(" ")


async def stdin_chat(model: str, max_tokens: int):
    content = sys.stdin.read()

    await AsyncMarvinClient().generate_chat(
        model=model,
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens,
        stream=True,
        stream_callback=print_chunk,
    )


async def chat_loop(model: str, max_tokens: int, fifo_path: str):
    message_history = deque(maxlen=20)  # 10 message pairs * 2

    # TODO manage history as a Thread that Assistants can subscribe and post to

    while True:
        with open(fifo_path, "r") as fifo:
            content = fifo.read()
            if content.strip():
                message_history.append({"role": "user", "content": content})
                sys.stdout.write("\n:: ")
                sys.stdout.flush()

                completion = await AsyncMarvinClient().generate_chat(
                    model=model,
                    messages=list(message_history),
                    max_tokens=max_tokens,
                    stream=True,
                    stream_callback=print_chunk,
                )

                assistant_message = completion.choices[0].message.content
                message_history.append(
                    {"role": "assistant", "content": assistant_message}
                )


def is_tmux_running() -> bool:
    """Check if tmux is currently running."""
    return os.getenv("TMUX") is not None


def chat():
    """
    Start a chat session in a tmux layout with left pane for input and right pane for responses.
    """
    if is_tmux_running():
        try:
            fifo_path = "/tmp/marvin_chat_fifo"
            if not os.path.exists(fifo_path):
                os.mkfifo(fifo_path)

            # Split the window and start the chat loop in the right pane
            tmux_command_chat = [
                "tmux",
                "split-window",
                "-h",
                "-p",
                "50",
                "bash",
                "-c",
                f'python -c \'from marvin.cli.chat import chat_loop; import asyncio; asyncio.run(chat_loop("gpt-3.5-turbo", 1000, "{fifo_path}"))\'',
            ]

            subprocess.run(tmux_command_chat)

            subprocess.run(["tmux", "select-pane", "-L"])

            while True:
                message = console.input(Text("> ", style="info"))

                with open(fifo_path, "w") as fifo:
                    fifo.write(message + "\n")

        except (subprocess.CalledProcessError, KeyboardInterrupt, EOFError) as e:
            if os.path.exists(fifo_path):
                os.unlink(fifo_path)
            if isinstance(e, KeyboardInterrupt):
                console.print(Text("\nChat session ended by user.", style="warning"))
            else:
                console.print(Text(f"\nChat session ended: {e}", style="error"))

            subprocess.run(["tmux", "kill-pane", "-t", "right"])

            raise typer.Exit(code=1)
    else:
        console.print(
            Text("tmux is not running. Please start tmux and try again.", style="error")
        )
        console.print(
            Text(
                "To start tmux, you can usually just type 'tmux' in your terminal.",
                style="info",
            )
        )
        raise typer.Exit(code=1)
