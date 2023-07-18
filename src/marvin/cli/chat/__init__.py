from rich.prompt import Prompt
from rich.console import Console
from rich.panel import Panel
from rich import box


def _reset_history():
    global history
    history = []
    console.print(Panel("History has been reset.", box=box.DOUBLE_EDGE, expand=False))


def _get_settings():
    import marvin.settings

    console.print(
        Panel(
            f"Settings:\n{marvin.settings.json(indent=2)}",
            box=box.DOUBLE_EDGE,
            expand=False,
        )
    )


KNOWN_COMMANDS = {
    "!refresh": _reset_history,
    "!settings": _get_settings,
}

console = Console()


def format_user_input(user_input):
    return f"[bold blue]You:[/bold blue] {user_input}"


def format_chatbot_response(response):
    return f"[bold green]Marvin:[/bold green] {response}"


async def chat():
    console.print(
        Panel(
            "[bold]Welcome to the Marvin Chat CLI![/bold]", box=box.DOUBLE, expand=False
        )
    )
    console.print(
        Panel("You can type 'quit' or 'exit' to end the conversation.", expand=False)
    )
    from marvin.engine.language_models import chat_llm
    from marvin.utilities.messages import Message

    global history
    history = []
    model = chat_llm()
    try:
        while True:
            user_input = Prompt.ask("❯ ")
            if (input_lower := user_input.lower()) in ["quit", "exit"]:
                break
            if input_lower in KNOWN_COMMANDS:
                KNOWN_COMMANDS[input_lower]()
                continue

            with console.status("[bold green]Processing...", spinner="dots"):
                user_message = Message(role="USER", content=user_input)
                response = await model.run(messages=history + [user_message])
                history.extend([user_message, response])
            console.print(
                Panel(
                    format_chatbot_response(response.content),
                    box=box.ROUNDED,
                    expand=False,
                ),
            )
    except KeyboardInterrupt:
        pass
