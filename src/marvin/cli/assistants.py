from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from pydantic import BaseModel, Field

from marvin.beta.assistants import Assistant
from marvin.tools.assistants import CodeInterpreter  # Adjusted import for Assistant

from . import threads as threads_cli

assistants_app = typer.Typer()
ROOT_DIR = Path.home() / ".marvin/cli/assistants"
CURRENT_ASSISTANT_FILE = ROOT_DIR / "current_assistant.json"
DEFAULT_NAME = "default"

# Ensure the root directory exists
ROOT_DIR.mkdir(parents=True, exist_ok=True)


class AssistantData(BaseModel):
    name: str
    assistant: Assistant
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CurrentAssistant(BaseModel):
    name: str
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def get_assistant_file_path(name: str) -> Path:
    return ROOT_DIR / f"{name}.json"


def set_current_assistant_name(name: str):
    current_assistant_data = CurrentAssistant(name=name)
    CURRENT_ASSISTANT_FILE.write_text(current_assistant_data.model_dump_json())


def get_current_assistant_name() -> Optional[str]:
    if CURRENT_ASSISTANT_FILE.exists():
        try:
            data = CURRENT_ASSISTANT_FILE.read_text()
            current_assistant_data = CurrentAssistant.model_validate_json(data)
            return current_assistant_data.name
        except Exception as e:
            raise ValueError(f"Error reading current assistant: {e}")
    raise ValueError("No current assistant found.")


def save_assistant(
    name: str, assistant: Optional[Assistant] = None, set_current: bool = True
) -> AssistantData:
    assistant = assistant or Assistant()  # Assuming Assistant() is valid
    assistant_data = AssistantData(name=name, assistant=assistant)
    assistant_file = get_assistant_file_path(name)
    assistant_file.write_text(assistant_data.model_dump_json())
    if set_current:
        set_current_assistant_name(name)
    return assistant_data


def get_assistant_data(name: str) -> Optional[AssistantData]:
    assistant_file = get_assistant_file_path(name)
    if assistant_file.exists():
        data = assistant_file.read_text()
        return AssistantData.model_validate_json(data)
    else:
        return None


def get_current_assistant_data() -> AssistantData:
    current_assistant_name = get_current_assistant_name()
    if current_assistant_name:
        return get_assistant_data(current_assistant_name)
    else:
        return save_assistant(DEFAULT_NAME, set_current=False)


# @assistants_app.command()
# def delete(
#     name: str = typer.Option(
#         ..., "--name", "-n", help="Name of the assistant to delete"
#     )
# ):
#     assistant_file = get_assistant_file_path(name)
#     if assistant_file.exists():
#         assistant_file.unlink()
#         typer.echo(f"Assistant '{name}' deleted.")
#     else:
#         typer.echo(f"Assistant '{name}' not found.")


# @assistants_app.command()
# def set(
#     name: str = typer.Argument(..., help="Name of the assistant to set as current")
# ):
#     assistant_data = get_assistant_data(name)
#     if assistant_data:
#         set_current_assistant_name(name)
#         typer.echo(f"Assistant '{name}' set as current.")
#     else:
#         typer.echo(f"Assistant '{name}' not found.")


# @assistants_app.command()
# def list():
#     assistants = [
#         file.stem
#         for file in ROOT_DIR.glob("*.json")
#         if file.stem != "current_assistant"
#     ]
#     assistants.sort(
#         key=lambda name: (
#             get_assistant_data(name).last_updated
#             if get_assistant_data(name)
#             else datetime.min
#         ),
#         reverse=True,
#     )
#     if assistants:
#         typer.echo("\n".join(assistants))
#     else:
#         typer.echo("No assistants found.")


@assistants_app.command()
def say(message, model: str = None):
    # try:
    #     name = get_current_assistant_name()
    #     data = get_assistant_data(name)
    #     assistant = data.assistant
    # except ValueError:
    #     assistant = Assistant(name="Marvin", tools=[CodeInterpreter])
    #     save_assistant(name="Marvin", assistant=assistant)
    assistant = Assistant(name="Marvin", tools=[CodeInterpreter])
    thread_name = threads_cli.get_current_thread_name()
    thread = threads_cli.get_thread_data(thread_name)
    assistant.say(message, thread=thread.thread, model=model)
    threads_cli.update_current_thread_last_updated()


if __name__ == "__main__":
    assistants_app()
