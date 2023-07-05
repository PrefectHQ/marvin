from typing import Callable, List, Union

from marvin import AIApplication
from marvin.prompts import Prompt
from marvin.tools.base import Tool

DEFAULT_NAME = "Marvin"
DEFAULT_PERSONALITY = "A friendly AI assistant"
DEFAULT_INSTRUCTIONS = "Engage the user in conversation."


class Chatbot(AIApplication):
    name: str = DEFAULT_NAME
    personality: str = DEFAULT_PERSONALITY
    instructions: str = DEFAULT_INSTRUCTIONS
    tools: List[Union[Tool, Callable]] = ([],)

    def __init__(
        self,
        name: str = DEFAULT_NAME,
        personality: str = DEFAULT_PERSONALITY,
        instructions: str = DEFAULT_INSTRUCTIONS,
        state=None,
        tools: list[Union[Tool, Callable]] = [],
        additional_prompts: list[Prompt] = None,
        **kwargs,
    ):
        description = f"""
            You are a chatbot - your name is {name}.
            
            You must respond to the user in accordance with
            your personality and instructions.
            
            Your personality is: {personality}.
            
            Your instructions are: {instructions}.
            """
        super().__init__(
            name=name,
            description=description,
            tools=tools,
            state=state or {},
            plan_enabled=False,
            additional_prompts=additional_prompts or [],
            **kwargs,
        )


__all__ = ["Chatbot"]
