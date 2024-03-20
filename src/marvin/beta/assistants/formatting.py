import functools
import inspect
import json
import tempfile
from datetime import datetime

from openai.types.beta.threads import Message
from openai.types.beta.threads.runs.run_step import RunStep
from partialjson import JSONParser
from rich import box
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel

from marvin.utilities.openai import get_openai_client

json_parser = JSONParser()


def format_step(step: RunStep) -> list[Panel]:
    @functools.lru_cache(maxsize=1000)
    def _cached_format_step(_step):
        """
        Closure that allows for caching of the formatted step. "_step" is a
        hashable identifier for the cache; the actual function reads the full
        "step" from the parent scope.
        """
        # Timestamp formatting
        timestamp = datetime.fromtimestamp(step.created_at).strftime("%l:%M:%S %p")

        # default content
        content = (
            f"Assistant is performing an action: {step.type} - Status:"
            f" {step.status}"
        )

        panels = []

        # attempt to customize content
        if step.type == "tool_calls":
            for tool_call in step.step_details.tool_calls:
                if tool_call.type == "code_interpreter":
                    panel_title = "Code Interpreter"
                    footer = []
                    for output in tool_call.code_interpreter.outputs:
                        if output.type == "logs":
                            content = inspect.cleandoc(
                                """
                                The code interpreter produced this result:
                                
                                ```python
                                {result}
                                ```
                                
                                {note}
                                """
                            )

                            if len(output.logs) > 500:
                                result = output.logs[:500] + " ..."
                                note = "*(First 500 characters shown)*"
                            else:
                                result = output.logs
                                note = ""
                            footer.append(content.format(result=output.logs, note=note))
                        elif output.type == "image":
                            # Use the download_temp_file function to download the file and get
                            # the local path
                            local_file_path = download_temp_file(
                                output.image.file_id, suffix=".png"
                            )
                            footer.append(
                                f"The code interpreter produced this image: [{local_file_path}]({local_file_path})"
                            )

                    content = inspect.cleandoc(
                        """
                        Running the code interpreter...
                        
                        ```python
                        {input}
                        ```
                        
                        {footer}
                        """
                    ).format(
                        input=tool_call.code_interpreter.input, footer="\n".join(footer)
                    )
                elif tool_call.type == "function":
                    panel_title = "Tool Call"
                    if step.status == "in_progress":
                        if tool_call.function.arguments:
                            try:
                                args = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                try:
                                    args = json_parser.parse(
                                        tool_call.function.arguments
                                    )
                                except Exception:
                                    args = tool_call.function.arguments

                            content = inspect.cleandoc(
                                """
                                Using the `{function}` tool with these arguments:
                                
                                ```python
                                {args}
                                ```
                                """
                            ).format(function=tool_call.function.name, args=args)

                        else:
                            content = f"Assistant wants to use the `{tool_call.function.name}` tool."

                    elif step.status == "completed":
                        if tool_call.function.output:
                            content = inspect.cleandoc(
                                """
                                The `{tool_name}` tool produced this result:
                                
                                ```python
                                {result}
                                ```
                                
                                {note}
                                """
                            )
                            if len(tool_call.function.output) > 500:
                                result = tool_call.function.output[:500] + " ..."
                                note = "*(First 500 characters shown)*"
                            else:
                                result = tool_call.function.output
                                note = ""
                            content = content.format(
                                tool_name=tool_call.function.name,
                                result=result,
                                note=note,
                            )
                        else:
                            content = f"The `{tool_call.function.name}` tool has completed with no result."

                # Create the panel for the run step status
                panels.append(
                    Panel(
                        Markdown(inspect.cleandoc(content)),
                        title=panel_title,
                        subtitle=f"[italic]{timestamp}[/]",
                        title_align="left",
                        subtitle_align="right",
                        border_style="gray74",
                        box=box.ROUNDED,
                        width=100,
                        expand=True,
                        padding=(1, 2),
                    )
                )

        elif step.type == "message_creation":
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


def format_message(message: Message) -> Panel:
    role_colors = {
        "user": "green",
        "assistant": "blue",
    }

    color = role_colors.get(message.role, "red")
    timestamp = (
        datetime.fromtimestamp(message.created_at).strftime("%I:%M:%S %p").lstrip("0")
    )

    content = []
    for item in message.content:
        if item.type == "text":
            content.append(item.text.value + "\n\n")
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
    panel = Panel(
        Markdown(inspect.cleandoc("\n\n".join(content))),
        title=f"[bold]{message.role.capitalize()}[/]",
        subtitle=f"[italic]{timestamp}[/]",
        title_align="left",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        # highlight=True,
        width=100,  # Fixed width for all panels
        expand=True,  # Panels always expand to the width of the console
        padding=(1, 2),
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
