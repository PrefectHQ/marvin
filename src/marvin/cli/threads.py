import os
from pathlib import Path
from typing import Optional

import typer
from pydantic import BaseModel, ValidationError

from marvin.beta.assistants import Thread
from marvin.utilities.openai import get_openai_client

threads_app = typer.Typer(no_args_is_help=True)
ROOT_DIR = Path.home() / ".marvin/cli/threads"
DEFAULT_THREAD_NAME = "default"

# Ensure the root directory exists
ROOT_DIR.mkdir(parents=True, exist_ok=True)


class ThreadData(BaseModel):
    name: str
    id: str


def get_thread_file_path(name: str) -> Path:
    return ROOT_DIR / f"{name}.json"


def save_thread(thread_data: ThreadData):
    thread_file = get_thread_file_path(thread_data.name)
    thread_file.write_text(thread_data.model_dump_json())


def load_thread(name: str) -> Optional[ThreadData]:
    thread_file = get_thread_file_path(name)
    if thread_file.exists():
        try:
            thread_data = ThreadData.model_validate_json(thread_file.read_text())
        except ValidationError:
            thread_file.unlink()
            return None
        return thread_data
    else:
        return None


def create_thread(name: str) -> ThreadData:
    thread = Thread()
    thread.create()
    thread_data = ThreadData(name=name, id=thread.id)
    save_thread(thread_data)
    return thread_data


def get_or_create_thread(name: str = None) -> ThreadData:
    name = name or os.getenv("MARVIN_CLI_THREAD", DEFAULT_THREAD_NAME)
    thread_data = load_thread(name)
    if thread_data is None:
        thread_data = create_thread(name)
    return thread_data


@threads_app.command()
def current():
    """Get the current thread's name."""
    thread_data = get_or_create_thread()
    typer.echo(f"Current thread: {thread_data.name} (ID: {thread_data.id})")


@threads_app.command()
def clear(
    thread: str = typer.Option(
        DEFAULT_THREAD_NAME,
        "--thread",
        "-t",
        help="Thread name",
        envvar="MARVIN_CLI_THREAD",
    ),
):
    thread_data = create_thread(thread)
    typer.echo(f"Thread '{thread_data.name}' cleared. New ID: {thread_data.id}")


@threads_app.command(help="Cancel the most recent run in a thread.")
def clear_run(
    thread: str = typer.Option(
        DEFAULT_THREAD_NAME,
        "--thread",
        "-t",
        help="Thread name",
        envvar="MARVIN_CLI_THREAD",
    ),
):
    thread_data = load_thread(thread)
    openai_client = get_openai_client(is_async=False)
    runs = openai_client.beta.threads.runs.list(thread_id=thread_data.id, limit=1)
    run = runs.data[0]

    if run.status != "cancelled":
        openai_client.beta.threads.runs.cancel(
            run_id=runs.data[0].id, thread_id=thread_data.id
        )
        typer.echo(f'Most recent run in thread "{thread_data.name}" cancelled.')


if __name__ == "__main__":
    threads_app()
