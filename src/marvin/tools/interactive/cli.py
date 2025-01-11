import inspect

from rich.prompt import Prompt as RichPrompt

from marvin.engine.orchestrator import get_current_orchestrator

INSTRUCTIONS = """
If a task requires you to interact with a user, it will show
`interactive=True` and you will be given this tool. You can use it to send
messages to the user and optionally wait for a response. This is how you
tell the user things and ask questions. Do not mention your tasks or the
workflow. The user can only see messages you send them via tool. They can
not read the rest of the thread. Do not send the user concurrent messages
that require responses, as this will cause confusion.

You may need to ask the human about multiple tasks at once. Consolidate your
questions into a single message. For example, if Task 1 requires information
X and Task 2 needs information Y, send a single message that naturally asks
for both X and Y.

Human users may give poor, incorrect, or partial responses. You may need to
ask questions multiple times in order to complete your tasks. Do not make up
answers for omitted information; ask again and only fail the task if you
truly can not make progress. If your task requires human interaction and
neither it nor any assigned agents have `interactive`, you can fail the
task.
"""


class Prompt(RichPrompt):
    # remove the prompt suffix
    prompt_suffix = " "


async def cli(message: str) -> str:
    """
    Send a message to a human user and wait for a response
    """
    orchestrator = get_current_orchestrator()
    if orchestrator:
        agent = orchestrator.active_agent().name
    else:
        agent = "Agent"

    result = Prompt.ask(
        inspect.cleandoc(
            f"""
            [bold blue]🤖 {agent}:[/] [blue]{message}[/]
            
            :computer: [bold green]You:[/]
            """
        )
    )
    return f"User response: {result}"
