import tempfile
from datetime import datetime

import openai
from openai.types.beta.threads import ThreadMessage
from openai.types.beta.threads.runs.run_step import RunStep
from rich import box
from rich.console import Console
from rich.panel import Panel

# def pprint_run(run: Run):
#     """
#     Runs are comprised of steps and messages, which are each in a sorted list
#     BUT the created_at timestamps only have second-level resolution, so we can't
#     easily sort the lists. Instead we walk them in order and combine them giving
#     ties to run steps.
#     """
#     index_steps = 0
#     index_messages = 0
#     combined = []

#     while index_steps < len(run.steps) and index_messages < len(run.messages):
#         if (run.steps[index_steps].created_at
#             <= run.messages[index_messages].created_at):
#             combined.append(run.steps[index_steps])
#             index_steps += 1
#         elif (
#             run.steps[index_steps].created_at
#             > run.messages[index_messages].created_at
#         ):
#             combined.append(run.messages[index_messages])
#             index_messages += 1

#     # Add any remaining items from either list
#     combined.extend(run.steps[index_steps:])
#     combined.extend(run.messages[index_messages:])

#     for obj in combined:
#         if isinstance(obj, RunStep):
#             pprint_run_step(obj)
#         elif isinstance(obj, ThreadMessage):
#             pprint_message(obj)


def pprint_run_step(run_step: RunStep):
    """
    Formats and prints a run step with status information.

    Args:
        run_step: A RunStep object containing the details of the run step.
    """
    # Timestamp formatting
    timestamp = datetime.fromtimestamp(run_step.created_at).strftime("%l:%M:%S %p")

    # default content
    content = (
        f"Assistant is performing an action: {run_step.type} - Status:"
        f" {run_step.status}"
    )

    # attempt to customize content
    if run_step.type == "tool_calls":
        for tool_call in run_step.step_details.tool_calls:
            if tool_call.type == "code_interpreter":
                if run_step.status == "in_progress":
                    content = "Assistant is running the code interpreter..."
                elif run_step.status == "completed":
                    content = "Assistant ran the code interpreter."
                else:
                    content = f"Assistant code interpreter status: {run_step.status}"
            elif tool_call.type == "function":
                if run_step.status == "in_progress":
                    content = (
                        "Assistant used the tool"
                        f" `{tool_call.function.name}` with arguments"
                        f" {tool_call.function.arguments}..."
                    )
                elif run_step.status == "completed":
                    content = (
                        "Assistant used the tool"
                        f" `{tool_call.function.name}` with arguments"
                        f" {tool_call.function.arguments}."
                    )
                else:
                    content = (
                        f"Assistant tool `{tool_call.function.name}` status:"
                        f" `{run_step.status}`"
                    )
    elif run_step.type == "message_creation":
        return

    console = Console()

    # Create the panel for the run step status
    panel = Panel(
        content.strip(),
        title="Assistant Run Step",
        subtitle=f"[italic]{timestamp}[/]",
        title_align="left",
        subtitle_align="right",
        border_style="gray74",
        box=box.ROUNDED,
        width=100,
        expand=True,
        padding=(0, 1),
    )
    # Printing the panel
    console.print(panel)


def download_temp_file(file_id: str, suffix: str = None):
    """
    Downloads a file from OpenAI's servers and saves it to a temporary file.

    Args:
        file_id: The ID of the file to be downloaded.
        suffix: The file extension to be used for the temporary file.

    Returns:
        The file path of the downloaded temporary file.
    """

    client = openai.Client()
    # file_info = client.files.retrieve(file_id)
    file_content_response = client.files.with_raw_response.retrieve_content(file_id)

    # Create a temporary file with a context manager to ensure it's cleaned up
    # properly
    with tempfile.NamedTemporaryFile(
        delete=False, mode="wb", suffix=f"{suffix}"
    ) as temp_file:
        temp_file.write(file_content_response.content)
        temp_file_path = temp_file.name  # Save the path of the temp file

    return temp_file_path


def pprint_message(message: ThreadMessage):
    """
    Pretty-prints a single message using the rich library, highlighting the
    speaker's role, the message text, any available images, and the message
    timestamp in a panel format.

    Args:
        message (ThreadMessage): A message object
    """
    console = Console()
    role_colors = {
        "user": "green",
        "assistant": "blue",
    }

    color = role_colors.get(message.role, "red")
    timestamp = (
        datetime.fromtimestamp(message.created_at).strftime("%I:%M:%S %p").lstrip("0")
    )

    content = ""
    for item in message.content:
        if item.type == "text":
            content += item.text.value + "\n\n"
        elif item.type == "image_file":
            # Use the download_temp_file function to download the file and get
            # the local path
            local_file_path = download_temp_file(item.image_file.file_id, suffix=".png")
            # Add a clickable hyperlink to the content
            file_url = f"file://{local_file_path}"
            content += (
                "[bold]Attachment[/bold]:"
                f" [blue][link={file_url}]{local_file_path}[/link][/blue]\n\n"
            )

    for file_id in message.file_ids:
        content += f"Attached file: {file_id}\n"

    # Create the panel for the message
    panel = Panel(
        content.strip(),
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

    # Printing the panel
    console.print(panel)


def pprint_messages(messages: list[ThreadMessage]):
    """
    Iterates over a list of messages and pretty-prints each one.

    Messages are pretty-printed using the rich library, highlighting the
    speaker's role, the message text, any available images, and the message
    timestamp in a panel format.

    Args:
        messages (list[ThreadMessage]): A list of ThreadMessage objects to be
            printed.
    """
    for message in messages:
        pprint_message(message)
