from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from pydantic import BaseModel, Field, ValidationError

from marvin.beta.assistants import Thread

threads_app = typer.Typer()
ROOT_DIR = Path.home() / ".marvin/cli/threads"
CURRENT_THREAD_FILE = ROOT_DIR / "current_thread.json"
DEFAULT_NAME = "default"

# Ensure the root directory exists
ROOT_DIR.mkdir(parents=True, exist_ok=True)


class ThreadData(BaseModel):
    name: str
    thread: Thread
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CurrentThread(BaseModel):
    name: str
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def get_thread_file_path(name: str) -> Path:
    return ROOT_DIR / f"{name}.json"


def set_current_thread_name(name: str):
    current_thread_data = CurrentThread(name=name)
    CURRENT_THREAD_FILE.write_text(current_thread_data.model_dump_json())


def get_current_thread_name() -> str:
    if CURRENT_THREAD_FILE.exists():
        try:
            data = CURRENT_THREAD_FILE.read_text()
            current_thread_data = CurrentThread.model_validate_json(data)
            return current_thread_data.name
        except Exception:
            save_thread(name=DEFAULT_NAME, thread=Thread(), set_current=True)
    else:
        save_thread(name=DEFAULT_NAME, thread=Thread(), set_current=True)


def save_thread(name: str, thread: Thread, set_current: bool = True) -> ThreadData:
    if not thread.id:
        thread.create()
    thread_data = ThreadData(name=name, thread=thread)
    thread_file = get_thread_file_path(name)
    thread_file.write_text(thread_data.model_dump_json())
    if set_current:
        set_current_thread_name(name)
    return thread_data


def get_thread_data(name: str) -> Optional[ThreadData]:
    thread_file = get_thread_file_path(name)

    if thread_file.exists():
        data = thread_file.read_text()
        try:
            return ThreadData.model_validate_json(data)
        except ValidationError:
            return save_thread(name, Thread(), set_current=False)
    else:
        return save_thread(name, Thread(), set_current=False)


def update_current_thread_last_updated():
    current_thread_name = get_current_thread_name()
    current_thread_data = get_thread_data(current_thread_name)
    save_thread(current_thread_name, current_thread_data.thread, set_current=True)


@threads_app.command()
def create(name: str = typer.Option(..., "--name", "-n", help="Name of the thread")):
    save_thread(name=name)
    typer.echo(f"Thread '{name}' created and set as current.")


@threads_app.command()
def reset():
    current_thread_name = get_current_thread_name()
    save_thread(name=current_thread_name, thread=Thread())
    typer.echo(f"Thread '{current_thread_name}' reset.")


@threads_app.command()
def delete(
    name: str = typer.Option(..., "--name", "-n", help="Name of the thread to delete"),
):
    thread_file = get_thread_file_path(name)
    if thread_file.exists():
        thread_file.unlink()
        typer.echo(f"Thread '{name}' deleted.")
    else:
        typer.echo(f"Thread '{name}' not found.")


@threads_app.command()
def set(name: str = typer.Argument(..., help="Name of the thread to set as current")):
    thread_data = get_thread_data(name)
    if thread_data:
        set_current_thread_name(name)
        typer.echo(f"Thread '{name}' set as current.")
    else:
        typer.echo(f"Thread '{name}' not found.")


@threads_app.command()
def list():
    threads = [
        file.stem for file in ROOT_DIR.glob("*.json") if file.stem != "current_thread"
    ]
    threads.sort(key=lambda name: get_thread_data(name).last_updated, reverse=True)
    if threads:
        typer.echo("\n".join(threads))
    else:
        typer.echo("No threads found.")


if __name__ == "__main__":
    threads_app()
