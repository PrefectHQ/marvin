import functools
import json
import tempfile
from datetime import datetime
from typing import Any, Union

from openai.types.beta.threads import Message
from openai.types.beta.threads.runs.run_step import RunStep
from partialjson import JSONParser
from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.syntax import Syntax

from marvin.utilities.openai import get_openai_client

json_parser = JSONParser()


@functools.lru_cache(maxsize=1000)
def download_temp_file(file_id: str, suffix: str = None):
    """
    Downloads a file from OpenAI's servers and saves it to a temporary file.

    Args:
        file_id: The ID of the file to be downloaded.
        suffix: The file extension to be used for the temporary file.

    Returns:
        The file path of the downloaded temporary file.
    """

    client = get_openai_client(is_async=False)
    response = client.files.content(file_id)

    # Create a temporary file with a context manager to ensure it's cleaned up
    # properly
    temp_file = tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=suffix)
    temp_file.write(response.content)

    return temp_file.name


def format_timestamp(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%l:%M:%S %p")


def create_panel(content: Any, title: str, timestamp: int, color: str):
    return Panel(
        content,
        title=f"[bold]{title}[/]",
        subtitle=f"[italic]{format_timestamp(timestamp)}[/]",
        title_align="left",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        width=100,
        expand=True,
        padding=(1, 2),
    )


def format_code_interpreter_tool_call(step, tool_call):
    panel_title = "Code Interpreter"
    code = Syntax(tool_call.code_interpreter.input, "python", padding=(1, 2))

    if not tool_call.code_interpreter.outputs:
        status = Status("Running code interpreter...", spinner="dots")
    else:
        status = ":heavy_check_mark: Finished!"
    content = Group(status, "\n", code)
    return create_panel(content, panel_title, step.created_at, "gray74")


def format_function_tool_call(step, tool_call):
    panel_title = "Tool Call"
    content = []
    if step.status == "in_progress":
        msg = f"Calling the [markdown.code]{tool_call.function.name}[/] tool with arguments:"
        args = parse_function_arguments(tool_call.function.arguments)
        arguments = Syntax(str(args), "python", padding=(0, 1))
        content = Columns([Status(msg, spinner="dots"), arguments])
    if step.status == "completed":
        content = f":heavy_check_mark: Received output from the [markdown.code]{tool_call.function.name}[/] tool."
    return create_panel(content, panel_title, step.created_at, "gray74")


@functools.lru_cache(maxsize=1000)
def parse_function_arguments(arguments: str) -> Union[dict, str]:
    try:
        return json.loads(arguments)
    except json.JSONDecodeError:
        try:
            return json_parser.parse(arguments)
        except Exception:
            return arguments


def format_step(step: RunStep) -> list[Panel]:
    @functools.lru_cache
    def _cached_format_step(_step):
        panels = []

        if step.type == "tool_calls":
            for tool_call in step.step_details.tool_calls:
                if tool_call.type == "code_interpreter":
                    panel = format_code_interpreter_tool_call(step, tool_call)
                elif tool_call.type == "function":
                    panel = format_function_tool_call(step, tool_call)
                panels.append(panel)

        elif step.type == "message_creation":
            # Handle message creation if necessary
            pass

        return Group(*panels)

    return _cached_format_step(step.model_dump_json())


def pprint_step(step: RunStep):
    """
    Formats and prints a run step with status information.

    Args:
        run_step: A RunStep object containing the details of the run step.
    """
    panel = format_step(step)

    if not panel:
        return

    console = Console()
    console.print(panel)


def pprint_steps(steps: list[RunStep]):
    """
    Iterates over a list of run steps and pretty-prints each one.

    Args:
        steps (list[RunStep]): A list of RunStep objects to be printed.
    """
    for step in sorted(steps, key=lambda s: s.created_at):
        pprint_step(step)


def format_message(message: Message) -> Panel:
    role_colors = {
        "user": "green",
        "assistant": "blue",
    }
    content = []
    for item in message.content:
        if item.type == "text":
            content.append(item.text.value)
        elif item.type == "image_file":
            # Use the download_temp_file function to download the file and get
            # the local path
            local_file_path = download_temp_file(item.image_file.file_id, suffix=".png")
            content.append(
                f"*View attached image: [{local_file_path}]({local_file_path})*"
            )

    for file_id in message.file_ids:
        content.append(f"Attached file: {file_id}\n")

    # Create the panel for the message
    panel = create_panel(
        Markdown("\n\n".join(content)),
        title=message.role.capitalize(),
        timestamp=message.created_at,
        color=role_colors.get(message.role, "red"),
    )
    return panel


def pprint_message(message: Message):
    """
    Pretty-prints a single message using the rich library, highlighting the
    speaker's role, the message text, any available images, and the message
    timestamp in a panel format.

    Args:
        message (Message): A message object
    """
    console = Console()
    panel = format_message(message)
    console.print(panel)


def pprint_messages(messages: list[Message]):
    """
    Iterates over a list of messages and pretty-prints each one.

    Messages are pretty-printed using the rich library, highlighting the
    speaker's role, the message text, any available images, and the message
    timestamp in a panel format.

    Args:
        messages (list[Message]): A list of Message objects to be
            printed.
    """
    for message in sorted(messages, key=lambda m: m.created_at):
        pprint_message(message)


def format_run(
    run, include_messages: bool = True, include_steps: bool = True
) -> list[Panel]:
    """
    Formats a run, which is an object that has both `.messages` and `.steps`
    attributes, each of which is a list of Messages and RunSteps.

    Args:
        run: A Run object
        include_messages: Whether to include messages in the formatted output
        include_steps: Whether to include steps in the formatted output
    """

    objects = []
    if include_messages:
        objects.extend([(format_message(m), m.created_at) for m in run.messages])
    if include_steps:
        objects.extend([(format_step(s), s.created_at) for s in run.steps])
    sorted_objects = sorted(objects, key=lambda x: x[1])
    return [x[0] for x in sorted_objects if x[0] is not None]


def pprint_run(run):
    """
    Pretty-prints a run, which is an object that has both `.messages` and
    `.steps` attributes, each of which is a list of Messages and RunSteps.

    Args:
        run: A Run object
    """
    console = Console()
    panels = format_run(run)
    console.print(Group(*panels))
