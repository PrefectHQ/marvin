import asyncio
import functools
import inspect
import re
from typing import Callable, TypeVar

from pydantic import BaseModel
from typing_extensions import ParamSpec

from marvin.engine.executors import OpenAIFunctionsExecutor
from marvin.engine.language_models.base import ChatLLM, chat_llm
from marvin.prompts import library as prompt_library
from marvin.tools.format_response import FormatResponse
from marvin.utilities.async_utils import run_sync
from marvin.utilities.types import safe_issubclass

T = TypeVar("T")
P = ParamSpec("P")

prompts = [
    prompt_library.System(content="""
        {% if instructions %}
        {{ instructions }}
        
        {% endif %}
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
        self,
        *,
        fn: Callable = None,
        name: str = None,
        description: str = None,
        model: ChatLLM = None,
        instructions: str = None,
    ):
        self._fn = fn
        self.model = model
        self.name = name or fn.__name__
        self.description = description or fn.__doc__
        self.instructions = instructions
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

    def map(self, *map_args: list, **map_kwargs: list):
        """
        Map the AI function over a sequence of arguments. Runs concurrently.

        Arguments should be provided as if calling the function normally, but
        each argument must be a list. The function is called once for each item
        in the list, and the results are returned in a list.

        For example, fn.map([1, 2]) is equivalent to [fn(1), fn(2)].

        fn.map([1, 2], x=['a', 'b']) is equivalent to [fn(1, x='a'), fn(2,
        x='b')].
        """

        coros = []

        i = 0
        while True:
            call_args = []
            call_kwargs = {}
            try:
                for arg in map_args:
                    call_args.append(arg[i])
                for k, v in map_kwargs.items():
                    call_kwargs[k] = v[i]
            except IndexError:
                break
            call_coro = self._call(*call_args, **call_kwargs)
            coros.append(call_coro)
            i += 1

        # gather returns a future, but run_sync requires a coroutine
        async def gather_coros():
            return await asyncio.gather(*coros)

        result = gather_coros()
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

        if self.model is None:
            model = chat_llm()
        else:
            model = self.model

        executor = OpenAIFunctionsExecutor(
            model=model,
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
                instructions=self.instructions,
            ),
        )

        return response.data["result"]

    def run(self, *args, **kwargs):
        # Override this to create the AI function as an instance method instead of
        # a passed function
        raise NotImplementedError()


def ai_fn(
    fn: Callable[P, T] = None, instructions: str = None, model: ChatLLM = None
) -> Callable[P, T]:
    """Decorator that transforms a Python function with a signature and docstring
    into a prompt for an AI to predict the function's output.

    Args:
        fn: The function to decorate - this function does not need source code

    Keyword Args:
        instructions: Added context for the AI to help it predict the function's output.

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
        return functools.partial(
            ai_fn, instructions=instructions, model=model
        )  # , **kwargs)
    return AIFunction(fn=fn, instructions=instructions, model=model)
