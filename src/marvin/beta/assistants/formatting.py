import tempfile
from datetime import datetime

import openai
from openai.types.beta.threads import ThreadMessage
from openai.types.beta.threads.runs.run_step import RunStep
from rich import box
from rich.console import Console
from rich.panel import Panel

from marvin.beta.assistants.assistants import Run


def print_run(run: Run):
    all_objects = sorted(run.steps + run.messages, key=lambda x: x.created_at)
    for obj in all_objects:
        if isinstance(obj, RunStep):
            print_run_step(obj)
        elif isinstance(obj, ThreadMessage):
            print_message(obj)


def print_run_step(run_step: RunStep):
    # Timestamp formatting
    timestamp = datetime.fromtimestamp(run_step.created_at).strftime("%I:%M:%S %p")
    # Content based on the run step type and status
    if run_step.type == "tool_calls":
        for tool_call in run_step.step_details.tool_calls:
            if tool_call.type == "code_interpreter":
                if run_step.status == "in_progress":
                    content = "Assistant is now running the code interpreter."
                elif run_step.status == "completed":
                    content = "Assistant has finished running the code interpreter."
                else:
                    content = f"Assistant code interpreter status: {run_step.status}"
    elif run_step.type == "message_creation":
        return
    else:
        content = (
            f"Assistant is performing an action: {run_step.type} - Status:"
            f" {run_step.status}"
        )

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


def print_message(message: ThreadMessage):
    """
    Pretty-prints a single message using the rich library, highlighting the
    speaker's role, the message text, any available images, and the message
    timestamp in a panel format.

    Args:
    message (dict): A message object as described in the API documentation.
    """
    console = Console()
    role_colors = {
        "user": "green",
        "assistant": "blue",
    }

    color = role_colors.get(message.role, "red")
    timestamp = datetime.fromtimestamp(message.created_at).strftime("%I:%M:%S %p")

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
