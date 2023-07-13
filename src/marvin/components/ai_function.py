import asyncio
import functools
from typing import Callable, TypeVar, Union

from pydantic import BaseModel

from marvin.engine.executors import OpenAIExecutor
from marvin.engine.language_models import ChatLLM
from marvin.functions import Function
from marvin.prompts import Prompt, render_prompts
from marvin.prompts.library import System, User
from marvin.tools.format_response import FormatResponse
from marvin.utilities.async_utils import run_sync
from marvin.utilities.types import safe_issubclass

T = TypeVar("T")
A = TypeVar("A")


class FunctionSystem(System):
    content = """\
        {% if prefix %}
        {{prefix}}
        
        {% endif %}
        {% if source_code %}
        Your job is to generate likely outputs for a Python function with the
        following signature and docstring:

        {{ source_code }}    
        
        {% endif %}
        The user will provide function inputs (if any) and you must respond with
        the most likely result.\
        {% if description %}
        
        
        The following function description was also provided:
        
        {{ description }}
        {% endif %}\
    """
    description: str = ""
    source_code: str = ""
    prefix: str = ""


class FunctionUser(User):
    content = """
        {% if arguments %} 
        The function was called with the following inputs:
        
        {%for (arg, value) in arguments.items()%}
        - {{ arg }}: {{ value }}
        {% endfor %}
        {% else %}
        The function was called without inputs.
        {% endif -%}
        What is its output?
    """
    arguments: dict = {}


class AIFunction(Function):
    def __init__(
        self,
        fn,
        *args,
        system: Union[str, Prompt] = None,
        user: Union[str, Prompt] = FunctionUser,
        model: ChatLLM = None,
        **kwargs,
    ):
        self.system = system
        self.user = user
        self.fn = fn
        super().__init__(*args, fn=fn, **kwargs)

    def __call__(self, *args, **kwargs):
        output = self._call_(*args, **kwargs)
        if not self.is_async:
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
            call_coro = self._call_(*call_args, **call_kwargs)
            coros.append(call_coro)
            i += 1

        # gather returns a future, but run_sync requires a coroutine
        async def gather_coros():
            return await asyncio.gather(*coros)

        result = gather_coros()
        if not self.is_async:
            result = run_sync(result)
        return result

    async def _call_(self, *args, **kwargs):
        executor = OpenAIExecutor(
            functions=[
                FormatResponse(type_=self.return_annotation).as_openai_function()
            ],
            function_call={"name": "FormatResponse"},
            max_iterations=1,
        )

        [response] = await executor.start(
            prompts=self.__prompts__,
            prompt_render_kwargs={
                "source_code": self.source_code,
                "description": self.description,
                "arguments": self.arguments(*args, **kwargs),
                "basemodel_response": safe_issubclass(
                    self.return_annotation, BaseModel
                ),
                **({"prefix": self.system} if type(self.system) == str else {}),
            },
        )
        return response.data.get("arguments").get("data")

    @property
    def __prompts__(self):
        if safe_issubclass(type(self.system), Prompt):
            return [self.system, self.user]
        else:
            return [FunctionSystem(), self.user()]

    def __messages__(self, *args, **kwargs):
        return render_prompts(
            self.__prompts__,
            render_kwargs={
                "source_code": self.source_code,
                "description": self.description,
                "arguments": self.arguments(*args, **kwargs),
                **({"prefix": self.system} if type(self.system) == str else {}),
            },
        )


def ai_fn(
    fn: Callable[[A], T] = None, *args, system=None, **kwargs
) -> Callable[[A], T]:
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
        return functools.partial(ai_fn, system=system, **kwargs)
    return AIFunction(fn=fn, system=system)
