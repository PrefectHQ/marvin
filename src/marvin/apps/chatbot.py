from marvin import AIApplication
from marvin.tools.base import Tool

DEFAULT_PERSONALITY = "A friendly AI assistant"
DEFAULT_INSTRUCTIONS = "Engage the user in conversation."


class Bot(AIApplication):
    personality: str = None
    instructions: str = None

    def __init__(
        self,
        personality: str = None,
        instructions: str = None,
        tools: list[Tool] = None,
        **kwargs,
    ):
        if personality is None:
            personality = DEFAULT_PERSONALITY
        if instructions is None:
            instructions = DEFAULT_INSTRUCTIONS
        description = """
            You are a chatbot. You must respond to the user in accordance with
            your personality and instructions.
            
            Your personality is: {{ app.personality }}
            
            Your instructions are: {{ app.instructions }}
            """
        super().__init__(
            personality=personality,
            instructions=instructions,
            description=description,
            tools=tools,
            **kwargs,
        )


__all__ = ["Bot"]
