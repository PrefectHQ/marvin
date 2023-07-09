import asyncio
import functools
import inspect
import re
from typing import Callable, TypeVar

from pydantic import BaseModel

from marvin.engine.executors import OpenAIExecutor
from marvin.prompts import library as prompt_library
from marvin.tools.format_response import FormatResponse
from marvin.utilities.types import safe_issubclass

T = TypeVar("T")
A = TypeVar("A")

prompts = [
    prompt_library.System(content="""
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
    prompt_library.User(content="""
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

        executor = OpenAIExecutor(
            functions=[FormatResponse(type_=return_annotation).as_openai_function()],
            function_call={"name": "FormatResponse"},
            max_iterations=1,
        )
        [response] = await executor.start(
            prompts=prompts,
            prompt_render_kwargs=dict(
                function_def=function_def,
                function_name=self.fn.__name__,
                function_description=(
                    self.description if self.description != self.fn.__doc__ else None
                ),
                basemodel_response=safe_issubclass(return_annotation, BaseModel),
                input_binds=bound_args.arguments,
            ),
        )

        return response.data["result"]

    def run(self, *args, **kwargs):
        # Override this to create the AI function as an instance method instead of
        # a passed function
        raise NotImplementedError()


def ai_fn(fn: Callable[[A], T] = None) -> Callable[[A], T]:
    """Decorator that transforms a Python function with a signature and docstring
    into a prompt for an AI to predict the function's output.

    Args:
        fn: The function to decorate - this function does not need source code

    Examples:
        Returns a word that rhymes with the input word.
        ```python
        @ai_fn
        def rhyme(word: str) -> str:
            "Returns a word that rhymes with the input word."

        rhyme("blue") # "glue"
        ```
        Produce a list of `Person` objects from unstructured text.
        ```python
        from pydantic import BaseModel, Field
        from marvin import ai_fn

        class Person(BaseModel):
            name: str
            age: int = Field(description="Age in years (age of death if deceased)")

        @ai_fn
        def parse_people(text: str) -> list[Person]:
            \"\"\" generates a list of people from some context \"\"\"

        parse_people("inventors of the telephone and assembly line")
        # [
        #   Person(name="Alexander Graham Bell", age=75),
        #   Person(name="Henry Ford", age=83)
        # ]
        ```

    """
    # this allows the decorator to be used with or without calling it
    if fn is None:
        return functools.partial(ai_fn)  # , **kwargs)
    return AIFunction(fn=fn)
