import asyncio
import functools
import inspect
import re
from typing import Callable, TypeVar, Tuple

from pydantic import BaseModel, validate_arguments

from marvin.engines.language_models import ChatLLM
from marvin.functions.prompts import render_prompts
from marvin.prompts.messages import System, User
from marvin.tools.format_response import FormatResponse
from marvin.utilities.types import safe_issubclass

T = TypeVar("T")
A = TypeVar("A")

ai_choice_prompts = [
    System(content="""
        {{ choice_context }}
        The user will provide context through text, you will you your expertise 
        to choose the best option below based on. 
        {% for option in options %}
            {{ loop.index }}. {{ option }}
        {% endfor %}
        """),
    User(content="""{{ input_text }}"""),
]


class AIChoice:
    def __init__(self, *, fn: Callable = None):
        if fn is None:
            fn = self.run
        self.fn = fn
        self.choice_context = self.fn.__doc__
        super().__init__()

    def __repr__(self):
        return f"<AIChoice {self.name}>"

    def __call__(self, *args, **kwargs):
        output = self._call(*args, **kwargs)
        if not inspect.iscoroutinefunction(self.fn):
            output = asyncio.run(output)
        return output

    @validate_arguments
    async def _call(self, query: str, options: list[str], **kwargs):
        if query and options:
            model = ChatLLM(
                max_tokens=1,  # only return one token
                temperature=0,  # only return the most likely token
            )

            messages = render_prompts(
                ai_choice_prompts,
                render_kwargs=dict(
                    input_text=query, options=options, choice_context=self.fn.__doc__
                ),
            )

            llm_call = model.run(
                messages=messages,
                logit_bias={  # bias the model to select an integer index
                    next(iter(model.get_tokens(str(i)))): 100
                    for i in range(1, len(options) + 1)
                },
            )
            response = asyncio.run(llm_call)
            selected_route = int(response.content) - 1
            return options[selected_route]


def ai_choice(fn: Callable[[A], T] = None) -> Callable[[A], T]:
    """
    @ai_choice
    def get_choices(query:str, options: list) -> str:
        '''You are classifying the opposite sentiment of incoming user test'''

    get_choices('I love twitter', ['happy', 'sad']) #happy
    """
    # this allows the decorator to be used with or without calling it
    if fn is None:
        return functools.partial(ai_choice)  # , **kwargs)
    return AIChoice(fn=fn)
