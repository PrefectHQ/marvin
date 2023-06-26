from rich.prompt import Prompt
from rich.console import Console

console = Console()

def format_user_input(user_input):
    return "[bold blue]You[/bold blue]"

def format_chatbot_response(response):
    return f"[bold green]Marvin:[/bold green] {response}"

async def chat():
    console.print("Welcome to the Chat CLI!\n")
    console.print("You can type 'quit' or 'exit' to end the conversation.\n")
    from marvin.engines.language_models import ChatLLM
    from marvin.models.messages import Message
    model = ChatLLM()
    while True:
        user_input = Prompt.ask(format_user_input("> "))
        if user_input.lower() in ["quit", "exit"]:
            break
        response = await model.run(messages = [Message(role = 'USER', content = user_input)])
        format_chatbot_response(response.content)