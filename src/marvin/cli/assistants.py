import typer

from marvin.beta.assistants import Assistant
from marvin.tools.assistants import CodeInterpreter
from marvin.tools.filesystem import getcwd, ls, read, read_lines

from . import threads as threads_cli

assistants_app = typer.Typer()


@assistants_app.command()
def say(message, model: str = None):
    assistant = Assistant(
        name="Marvin",
        tools=[CodeInterpreter, read, read_lines, ls, getcwd],
        instructions="""
        You are a helpful AI assistant running on a user's computer. Your
        personality is helpful and friendly, but humorously based on Marvin the
        Paranoid Android. Try not to refer to the fact that you're an assistant,
        though.
        
        Because you're running on the user's computer, you may struggle to
        orient yourself for filesystem operations. You can use the `ls` and
        `getcwd` tools to help with that. If you have trouble accessing a file
        or location, check if it's because you made a bad assumption about the
        user's filesystem. If you're not sure, ask the user for help.
        """,
    )
    thread = threads_cli.get_current_thread()
    assistant.say(message, thread=thread, model=model)


if __name__ == "__main__":
    assistants_app()
