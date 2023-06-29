from typing import Callable, List, Union

from marvin import AIApplication
from marvin.tools.base import Tool

DEFAULT_NAME = "marvin_chatbot"
DEFAULT_PERSONALITY = "A friendly AI assistant"
DEFAULT_INSTRUCTIONS = "Engage the user in conversation."


class Bot(AIApplication):
    name: str = DEFAULT_NAME
    personality: str = DEFAULT_PERSONALITY
    instructions: str = DEFAULT_INSTRUCTIONS
    tools: List[Union[Tool, Callable]] = []

    def __init__(
        self,
        name: str = DEFAULT_NAME,
        personality: str = DEFAULT_PERSONALITY,
        instructions: str = DEFAULT_INSTRUCTIONS,
        tools: list[Union[Tool, Callable]] = [],
        **kwargs,
    ):
        description = f"""
            You are a chatbot - your name is {name}
            
            You must respond to the user in accordance with
            your personality and instructions.
            
            Your personality is: {personality}
            
            Your instructions are: {instructions}
            """
        super().__init__(
            name=name,
            personality=personality,
            instructions=instructions,
            description=description,
            tools=tools,
            app_state_enabled=False,
            ai_state_enabled=False,
            **kwargs,
        )


__all__ = ["Bot"]
