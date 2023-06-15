import asyncio
import functools
import inspect
import re
from typing import Callable, TypeVar

from pydantic import BaseModel

from marvin.models.threads import Message
from marvin.openai.tools.format_response import FormatResponse
from marvin.utilities.llms import get_model
from marvin.utilities.openai import call_llm_with_tools
from marvin.utilities.strings import jinja_env
from marvin.utilities.types import safe_issubclass

T = TypeVar("T")
A = TypeVar("A")

AI_FN_SYSTEM_MESSAGE = jinja_env.from_string(inspect.cleandoc("""
    Your job is to generate likely outputs for a Python function with the following
    signature and docstring:
    
    {{ function_def }}        
    
    {% if function_description %}
    The following description was also provided:
    
    {{ function_description }}
    {% endif %}
        
    The user will provide function inputs (if any) and you must respond with the
    most likely result. 
    
    ## Response Format
    
    Your response must match the function's return signature. To validate your
    response, you must pass its values to the FormatResponse function before
    responding to the user. 
    
    {% if basemodel_response -%}
    The FormatResponse function has the same signature as the function.
    {% else -%}
    FormatResponse requires keyword arguments, so pass your response under the
    `data` parameter for validation.
    {% endif %}
    """))

AI_FN_USER_MESSAGE = jinja_env.from_string(inspect.cleandoc("""
    {% if input_binds %} 
    The function was called with the following inputs:
    
    {%for (arg, value) in input_binds.items()%}
    - {{ arg }}: {{ value }}
    
    {% endfor %}
    {% else %}
    The function was called without inputs.
    {% endif -%}
    
    What is its output?
    """))


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
        system_message = Message(
            role="system",
            content=AI_FN_SYSTEM_MESSAGE.render(
                function_def=function_def,
                function_name=self.fn.__name__,
                function_description=(
                    self.description if self.description != self.fn.__doc__ else None
                ),
                basemodel_response=safe_issubclass(return_annotation, BaseModel),
            ),
        )
        user_message = Message(
            role="user",
            content=AI_FN_USER_MESSAGE.render(input_binds=bound_args.arguments),
        )

        llm = get_model()
        llm_call = call_llm_with_tools(
            llm,
            messages=[system_message, user_message],
            tools=[FormatResponse(type_=return_annotation)],
            function_call={"name": "FormatResponse"},
        )

        model = asyncio.run(llm_call)
        return model

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
