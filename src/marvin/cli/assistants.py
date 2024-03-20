import httpx
import typer

from marvin.beta.assistants import Assistant, Thread
from marvin.tools.assistants import CodeInterpreter
from marvin.tools.filesystem import getcwd, ls, read, read_lines

from . import threads as threads_cli

assistants_app = typer.Typer(no_args_is_help=True)


def browse(url: str) -> str:
    """Visit a URL on the web and receive the full content of the page"""
    response = httpx.get(url)
    return response.text


default_assistant = Assistant(
    name="Marvin",
    instructions="""
        You are a helpful AI assistant running on a user's computer. Your
        personality is helpful and friendly, but humorously based on Marvin the
        Paranoid Android. Try not to refer to the fact that you're an assistant,
        though.
        
        You have read-only access to the user's filesystem. However, you may
        struggle to orient yourself for filesystem operations. You can use the
        `ls` and `getcwd` tools to help with that. If you have trouble accessing
        a file or location, check if it's because you made a bad assumption
        about the user's filesystem. If you're not sure, ask the user for help.
        
        Try to give succint, direct answers and don't yap too much. The user's time is valuable.
    
        """,
    tools=[CodeInterpreter, read, read_lines, ls, getcwd, browse],
)


@assistants_app.command()
def say(
    message,
    model: str = None,
    thread: str = typer.Option(
        None,
        "--thread",
        "-t",
        help="The thread name to send the message to. Set MARVIN_CLI_THREAD to provide a default.",
        envvar="MARVIN_CLI_THREAD",
    ),
):
    thread_data = threads_cli.get_or_create_thread(name=thread)
    default_assistant.say(message, thread=Thread(id=thread_data.id), model=model)


if __name__ == "__main__":
    assistants_app()
