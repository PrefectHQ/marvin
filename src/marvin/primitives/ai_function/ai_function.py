import asyncio
import functools
import inspect
import re
from typing import Callable, TypeVar

from pydantic import BaseModel

from marvin.engines.language_models import ChatLLM
from marvin.functions.prompts import render_prompts
from marvin.prompts.messages import System, User
from marvin.tools.format_response import FormatResponse
from marvin.utilities.types import safe_issubclass

T = TypeVar("T")
A = TypeVar("A")

prompts = [
    System(content="""
        Your job is to generate likely outputs for a Python function with the
        following signature and docstring:
    
        {{ function_def }}        
        
        The user will provide function inputs (if any) and you must respond with
        the most likely result. 
        
        {% if function_description %}
        The following function description was also provided:

        {{ function_description }}
        {% endif %}
        
        ## Response Format
        
        Your response must match the function's return signature. To validate your
        response, you must pass its values to the FormatResponse function before
        responding to the user. 
        
        {% if basemodel_response -%}
        `FormatResponse` has the same signature as the function.
        {% else -%}
        `FormatResponse` requires keyword arguments, so pass your response under
        the `data` parameter for validation.
        {% endif %}
        """),
    User(content="""
        {% if input_binds %} 
        The function was called with the following inputs:
        
        {%for (arg, value) in input_binds.items()%}
        - {{ arg }}: {{ value }}
        
        {% endfor %}
        {% else %}
        The function was called without inputs.
        {% endif -%}
        
        What is its output?
        """),
]


class AIFunction:
    def __init__(
        self, *, fn: Callable = None, name: str = None, description: str = None
    ):
        if fn is None:
            fn = self.run
        self.fn = fn

        self.name = name or fn.__name__
        self.description = description or fn.__doc__

        super().__init__()

    def __repr__(self):
        return f"<AIFunction {self.name}>"

    def __call__(self, *args, **kwargs):
        output = self._call(*args, **kwargs)

        # if the provided fn is not async, run it immediately
        if not inspect.iscoroutinefunction(self.fn):
            output = asyncio.run(output)

        return output

    async def _call(self, *args, **kwargs):
        # Get function signature
        sig = inspect.signature(self.fn)

        # get return annotation
        if sig.return_annotation is inspect._empty:
            return_annotation = str
        else:
            return_annotation = sig.return_annotation

        # get the function source code - it might include the @ai_fn decorator,
        # which can confuse the AI, so we use regex to only get the function
        # that is being decorated
        function_def = inspect.cleandoc(inspect.getsource(self.fn))
        if match := re.search(re.compile(r"(\bdef\b.*)", re.DOTALL), function_def):
            function_def = match.group(0)

        # Bind the provided arguments to the function signature
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # build the message
        messages = render_prompts(
            prompts,
            render_kwargs=dict(
                function_def=function_def,
                function_name=self.fn.__name__,
                function_description=(
                    self.description if self.description != self.fn.__doc__ else None
                ),
                basemodel_response=safe_issubclass(return_annotation, BaseModel),
                input_binds=bound_args.arguments,
            ),
        )
        model = ChatLLM()
        response = await model.run(
            messages=messages,
            functions=[FormatResponse(type_=return_annotation).as_openai_function()],
            function_call={"name": "FormatResponse"},
        )

        return response.data["result"]

    def run(self, *args, **kwargs):
        """
        Override this to create the AI function as an instance method instead of
        a passed function
        """
        raise NotImplementedError()


def ai_fn(fn: Callable[[A], T] = None) -> Callable[[A], T]:
    """
    @ai_fn
    def rhyme(word: str) -> str:
        "Returns a word that rhymes with the input word."

    rhyme("blue") # "glue"
    """
    # this allows the decorator to be used with or without calling it
    if fn is None:
        return functools.partial(ai_fn)  # , **kwargs)
    return AIFunction(fn=fn)
