import asyncio
import functools
import inspect
import re
from typing import Callable, TypeVar

from pydantic import BaseModel

from marvin.engine.executors import OpenAIExecutor
from marvin.prompts import library as prompt_library
from marvin.tools.format_response import FormatResponse
from marvin.utilities.async_utils import run_sync
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
        self._fn = fn
        self.name = name or fn.__name__
        self.description = description or fn.__doc__
        self.__signature__ = inspect.signature(fn)

        super().__init__()

    @property
    def fn(self):
        """
        Return's the `run` method if no function was provided, otherwise returns
        the function provided at initialization.
        """
        if self._fn is None:
            return self.run
        else:
            return self._fn

    def is_async(self):
        """
        Returns whether self.fn is an async function.

        This is used to determine whether to invoke the AI function on call, or
        return an awaitable.
        """
        return inspect.iscoroutinefunction(self.fn)

    def __repr__(self):
        return f"<AIFunction {self.name}>"

    def __call__(self, *args, **kwargs):
        output = self._call(*args, **kwargs)
        if not self.is_async():
            output = run_sync(output)

        return output

    def map(
        self,
        items: list = None,
        map_args: list[tuple] = None,
        map_kwargs: list[dict] = None,
    ):
        """
        Map the AI function over an iterable of arguments. Runs concurrently.

        Users can provide either `items`, or a combination of `map_args` and
        `map_kwargs`:
            - if `items` is provided, the AI function is called on each item in
                the list
            - if `map_args` and/or `map_kwargs` are provided, they are zipped and
                appropriately splatted into the AI function call as *args and
            **kwargs

        For example:

        @ai_fn
        def example(a, b=1):
            ...

        # calls example(1), example(2)
        example.map([1, 2])

        # calls example(1), example(2)
        example.map(map_args=[(1,), (2,)]

        # calls example(a=1), example(a=2)
        example.map(map_kwargs=[{"a": 1}, {"a": 2}]

        # calls example(a=1), example(a=2, b=100)
        example.map(map_kwargs=[{"a": 1}, {"a": 2, "b":100}]
        """
        if (map_args or map_kwargs) and items:
            raise ValueError("map_args and map_kwargs cannot be used with items")
        elif not map_args and not map_kwargs and not items:
            raise ValueError(
                "At least one of items, map_args, or map_kwargs is required"
            )

        if items:
            map_args = [(i,) for i in items]
            map_kwargs = [{}] * len(items)
        elif map_args is None:
            map_args = [()] * len(map_kwargs)
        elif map_kwargs is None:
            map_kwargs = [{}] * len(map_args)
        elif len(map_args) != len(map_kwargs):
            raise ValueError("map_args and map_kwargs must be the same length")

        # gather returns a future, but run_sync requires a coroutine
        async def gather_coro():
            return await asyncio.gather(
                *[self._call(*a, **k) for a, k in zip(map_args, map_kwargs)]
            )

        result = gather_coro()
        if not self.is_async():
            result = run_sync(result)
        return result

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

    Example:
        Returns a word that rhymes with the input word.
        ```python
        @ai_fn
        def rhyme(word: str) -> str:
            "Returns a word that rhymes with the input word."

        rhyme("blue") # "glue"
        ```
    """
    # this allows the decorator to be used with or without calling it
    if fn is None:
        return functools.partial(ai_fn)  # , **kwargs)
    return AIFunction(fn=fn)
