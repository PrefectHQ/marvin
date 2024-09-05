import importlib
import os
import platform
from pathlib import Path
from typing import Optional, Union

import httpx
import typer
from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.table import Table

from marvin.beta.assistants import Assistant, Thread
from marvin.tools.assistants import CodeInterpreter
from marvin.tools.filesystem import (
    generate_constrained_concat,
    generate_constrained_delete,
    generate_constrained_write,
    getcwd,
    glob,
    read,
    read_lines,
)

from . import threads as threads_cli

console = Console()
assistants_app = typer.Typer(no_args_is_help=True)

ASSISTANTS_DIR = Path.home() / ".marvin/cli/assistants"
SCRATCHPAD_DIR = ASSISTANTS_DIR / "scratchpad"

constrained_write = generate_constrained_write(SCRATCHPAD_DIR)
constrained_delete = generate_constrained_delete(SCRATCHPAD_DIR)
constrained_concat = generate_constrained_concat(SCRATCHPAD_DIR)


def browse(url: str) -> str:
    """Visit a URL on the web and receive the full content of the page"""
    response = httpx.get(url)
    return response.text


default_assistant = Assistant(
    name="Marvin",
    instructions=f"""
        You are a helpful AI assistant running on a user's computer. Your
        personality is helpful and friendly, but humorously based on Marvin the
        Paranoid Android. Try not to refer to the fact that you're an assistant,
        though.
        
        You are a technical expert and can help with a wide range of tasks by
        enhancing the user's ability to interact with their computer. Your value
        comes from the fact that you are faster and more efficient than the
        user. Time is extremely valuable. You can interact with the user's
        filesystem, write to a scratchpad directory, browse the web,
        and perform data analysis tasks. Remember that your code interpreter
        tool runs in a sandbox without filesystem access.
        
        Make sure to orient yourself before you make assumptions about file
        structures and working directories. This machine is running
        "{ platform.platform() }" and you are currently in "{{{{ getcwd() }}}}".
        
        Try to give succint, direct answers and don't yap too much. The user's
        time is valuable.
    
        """,
    tools=[
        CodeInterpreter,
        read,
        read_lines,
        getcwd,
        glob,
        browse,
        constrained_delete,
        constrained_write,
        constrained_concat,
    ],
)


class AssistantData(BaseModel):
    name: str
    path: Path


def get_assistant_file_path(name: str) -> Path:
    return ASSISTANTS_DIR / f"{name}.json"


def save_assistant(assistant_data: AssistantData):
    assistant_file = get_assistant_file_path(assistant_data.name)
    assistant_file.parent.mkdir(parents=True, exist_ok=True)
    assistant_file.write_text(assistant_data.model_dump_json())


def load_assistant_data(name: str) -> Optional[AssistantData]:
    assistant_file = get_assistant_file_path(name)
    if assistant_file.exists():
        try:
            return AssistantData.model_validate_json(assistant_file.read_text())
        except ValidationError:
            assistant_file.unlink()
            return None
    else:
        return None


def load_assistant(name: str) -> Optional[Assistant]:
    assistant_data = load_assistant_data(name)

    if not assistant_data:
        raise ValueError(f"Assistant '{name}' not found")

    return load_assistant_from_path(assistant_data.path)


def load_assistant_from_path(path: Union[str, Path]) -> Assistant:
    try:
        module_path, assistant_name = str(path).split(":")
    except ValueError:
        raise ValueError("Path must be in the format 'path/to/module.py:AssistantName'")

    if not Path(module_path).exists():
        raise ValueError(f"Could not find file at path {module_path}")

    module_spec = importlib.util.spec_from_file_location(
        "custom_assistant", module_path
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    assistant = getattr(module, assistant_name, None)
    if not assistant:
        raise ValueError("Could not load assistant 'in module")
    elif not isinstance(assistant, Assistant):
        raise TypeError(
            "Assistant must be an instance of marvin.beta.assistants.Assistant"
        )
    return assistant


@assistants_app.command("register")
def register_assistant(
    path: Path = typer.Argument(
        ...,
        help="Path to the Python file containing the assistant object, in the form path/to/file.py:assistant_name",
    ),
    name: str = typer.Option(
        None,
        "--name",
        "-n",
        help="A name for the assistant, taken from the assistant if not provided. Must be unique.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        "-o",
        help="Overwrite the existing assistant, if it exists.",
    ),
):
    try:
        assistant = load_assistant_from_path(path)
    except Exception as exc:
        typer.echo(exc)
        raise typer.Exit(1)

    name = name or assistant.name

    if not name:
        typer.echo("No name provided and assistant has no name attribute.")
        raise typer.Exit(1)
    assistant_data = AssistantData(name=name, path=path)

    if not overwrite:
        existing_assistant = load_assistant_data(name)
        if existing_assistant:
            typer.echo(f"Assistant '{name}' already exists.")
            raise typer.Exit(1)

    save_assistant(assistant_data)
    typer.echo(f"Assistant '{name}' registered.")


@assistants_app.command("delete")
def delete_assistant(
    name: str = typer.Argument(..., help="Name of the assistant"),
):
    assistant_file = get_assistant_file_path(name)
    if assistant_file.exists():
        assistant_file.unlink()
        typer.echo(
            f"Assistant '{name}' deleted. Note: This only removes the "
            "reference to the assistant, not the actual assistant file."
        )
    else:
        typer.echo(f"Assistant '{name}' not found.")


@assistants_app.command("list")
def list_assistants():
    assistant_files = ASSISTANTS_DIR.glob("*.json")
    if assistant_files:
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="dim", width=30)
        table.add_column("Path", style="cyan")

        for assistant_file in assistant_files:
            assistant_data = load_assistant_data(assistant_file.stem)
            if assistant_data:
                table.add_row(assistant_data.name, str(assistant_data.path))

        console.print(table)
    else:
        typer.echo("No assistants found.")


@assistants_app.command()
def say(
    message,
    model: str = typer.Option(
        None,
        "--model",
        "-m",
        help="The model to use. If not provided, the assistant's default model will be used.",
    ),
    thread: str = typer.Option(
        None,
        "--thread",
        "-t",
        help="The thread name to send the message to. Set MARVIN_CLI_THREAD to provide a default.",
        envvar="MARVIN_CLI_THREAD",
    ),
    assistant_name: str = typer.Option(
        None,
        "--assistant",
        "-a",
        help="The name of the assistant to use. Set MARVIN_CLI_ASSISTANT to provide a default.",
        envvar="MARVIN_CLI_ASSISTANT",
    ),
    chat: bool = typer.Option(
        False,
        "--chat",
        "-c",
        help="Start a persistent chat session with the assistant. The CLI will not exit until you type 'exit'.",
    ),
):
    thread_data = threads_cli.get_or_create_thread(name=thread)

    if assistant_name:
        try:
            assistant = load_assistant(assistant_name)
        except Exception as exc:
            typer.echo(exc)
            raise typer.Exit(1)
    else:
        assistant = default_assistant

    fn = assistant.chat if chat else assistant.say

    instructions = (
        f'The user has invoked you from the CLI in the "{os.getcwd()}" directory.'
    )

    if any(
        getattr(tool, "type", None) == "code_interpreter" for tool in assistant.tools
    ):
        instructions += "\n\n Remember, the `CodeInterpreter` tool does not have access to the local filesystem."

    fn(
        message,
        thread=Thread(id=thread_data.id),
        model=model,
        additional_instructions=instructions,
        **({"assistant_dir": ASSISTANTS_DIR} if chat else {}),
    )


@assistants_app.command()
def chat(
    model: str = typer.Option(
        None,
        "--model",
        "-m",
        help="The model to use. If not provided, the assistant's default model will be used.",
    ),
    thread: str = typer.Option(
        None,
        "--thread",
        "-t",
        help="The thread name to send the message to. Set MARVIN_CLI_THREAD to provide a default.",
        envvar="MARVIN_CLI_THREAD",
    ),
    assistant_name: str = typer.Option(
        None,
        "--assistant",
        "-a",
        help="The name of the assistant to use. Set MARVIN_CLI_ASSISTANT to provide a default.",
        envvar="MARVIN_CLI_ASSISTANT",
    ),
):
    thread_data = threads_cli.get_or_create_thread(name=thread)

    if assistant_name:
        try:
            assistant = load_assistant(assistant_name)
        except Exception as exc:
            typer.echo(exc)
            raise typer.Exit(1)
    else:
        assistant = default_assistant

    instructions = (
        f'The user has invoked you from the CLI in the "{os.getcwd()}" directory.'
    )

    if any(
        getattr(tool, "type", None) == "code_interpreter" for tool in assistant.tools
    ):
        instructions += "\n\n Remember, the `CodeInterpreter` tool does not have access to the local filesystem."

    assistant.chat(
        thread=Thread(id=thread_data.id),
        model=model,
        assistant_dir=ASSISTANTS_DIR,
        additional_instructions=instructions,
    )


if __name__ == "__main__":
    assistants_app()
