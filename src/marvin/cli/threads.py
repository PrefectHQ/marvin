from pathlib import Path

import typer

from marvin.beta.assistants import Thread

threads_app = typer.Typer()
ROOT_DIR = Path.home() / ".marvin/cli/threads"
CURRENT_THREAD_FILE = ROOT_DIR / "_current_thread.json"

# Ensure the root directory exists
ROOT_DIR.mkdir(parents=True, exist_ok=True)


def get_current_thread_id() -> str:
    if CURRENT_THREAD_FILE.exists():
        try:
            return CURRENT_THREAD_FILE.read_text().strip()
        except Exception:
            return reset_current_thread()
    else:
        return reset_current_thread()


def get_current_thread() -> Thread:
    thread_id = get_current_thread_id()
    return Thread(id=thread_id)


def set_current_thread_id(thread_id: str):
    CURRENT_THREAD_FILE.write_text(thread_id)


def reset_current_thread() -> str:
    thread = Thread()
    thread.create()
    set_current_thread_id(thread.id)
    return thread.id


@threads_app.command()
def current():
    thread_id = get_current_thread_id()
    typer.echo(f"Current thread ID: {thread_id}")


@threads_app.command()
def reset():
    thread_id = reset_current_thread()
    typer.echo(f"New thread created and set as current. Thread ID: {thread_id}")


if __name__ == "__main__":
    threads_app()
