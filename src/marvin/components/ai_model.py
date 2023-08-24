import asyncio
import functools
import inspect
from datetime import datetime
from typing import Any, Callable, Literal, Optional, TypeVar
from zoneinfo import ZoneInfo

from jinja2 import Template

from marvin.core.ChatCompletion import ChatCompletion
from marvin.pydantic import BaseModel
from marvin.types import Function, FunctionRegistry

T = TypeVar("T")


def default_context(text: str) -> dict:
    return {
        "The current date is": datetime.now(ZoneInfo("UTC")).strftime(
            "%A, %d %B %Y at %I:%M:%S %p %Z"
        )
    }


system_extract_prompt = inspect.cleandoc(
    "The user will provide context as text that you need to parse into a structured"
    " form.\n    - To validate your response, you must call the"
    " `{{functions[0].__name__}}` function. \n    - Use the provided text to extract or"
    " infer any parameters needed by `{{functions[0].__name__}}`, including any missing"
    " data. \n{% if get_context %}You have been provided the following context to"
    " perform your task:\n{%for (arg, value) in get_context(text).items()%}    - {{ arg"
    " }}: {{ value }}\n{% endfor %}{% endif %}"
)


system_generate_prompt = inspect.cleandoc(
    "The user will provide context as text that you need to parse to "
    "generate synthetic data.\n"
    "    - To validate your response, you must call the "
    "`{{functions[0].__name__}}` function.\n"
    "    - Use the provided text to generate or invent any parameters needed "
    "by `{{functions[0].__name__}}`, including any missing data.\n"
    "    - It is okay to make up representative data.\n"
    "{% if get_context %}"
    "You have been provided the following context to perform your task:\n"
    "{%for (arg, value) in get_context(text).items()%}"
    "    - {{ arg }}: {{ value }}\n"
    "{% endfor %}"
    "{% endif %}"
)

user_prompt = inspect.cleandoc("""\
    The text to parse: {{text}}
    """)


class AIModel(BaseModel):
    def __init__(self, *args, **kwargs):
        if text := next(iter(args), None):
            kwargs.update(self.__class__.call(text))
        super().__init__(**kwargs)

    @classmethod
    def prompt(cls, text: str = None, *args, __schema__=True, **kwargs):
        response = {}
        response["functions"] = cls._functions(*args, **kwargs)
        response["function_call"] = cls._function_call(
            *args, __schema__=__schema__, **kwargs
        )
        response["messages"] = cls._messages(
            text=text, functions=response["functions"], **kwargs
        )
        if __schema__:
            response["functions"] = response["functions"].schema()
        return response

    @classmethod
    def _messages(cls, **kwargs):
        return [
            {
                "role": role,
                "content": (
                    Template(kwargs.get(role, ""))
                    .render(
                        {
                            **kwargs,
                        }
                    )
                    .strip()
                ),
            }
            for role in ["system", "user"]
        ]

    @classmethod
    def _functions(cls, *args, **kwargs):
        return FunctionRegistry([Function.from_model(cls)])

    @classmethod
    def _function_call(cls, *args, __schema__=True, **kwargs):
        if __schema__:
            return {"name": cls._functions(*args, **kwargs).schema()[0].get("name")}
        return {"name": cls._functions(*args, **kwargs)[0].__name__}

    @classmethod
    def as_decorator(
        cls,
        base_model=None,
        instructions: str = None,
        system: str = None,
        user: str = user_prompt,
        get_context: Optional[Callable[[str], dict]] = default_context,
        mode: Literal["extract", "generate"] = "extract",
        model: Any = None,
        **model_kwargs,
    ):
        if not base_model:
            return functools.partial(
                cls.as_decorator,
                instructions=instructions,
                system=system
                or (
                    system_extract_prompt
                    if mode == "extract"
                    else system_generate_prompt
                ),
                user=user or user_prompt,
                model=model,
                get_context=get_context,
                **model_kwargs,
            )
        return type(
            base_model.__name__,
            (cls,),
            {
                **dict(base_model.__dict__),
                "_messages": functools.partial(
                    cls._messages,
                    instructions=instructions,
                    system=system
                    or (
                        system_extract_prompt
                        if mode == "extract"
                        else system_generate_prompt
                    ),
                    user=user or user_prompt,
                    get_context=get_context,
                ),
            },
        )

    @classmethod
    def to_chat_completion(cls, *args, __schema__=False, **kwargs):
        return ChatCompletion(**cls.prompt(*args, __schema__=__schema__, **kwargs))

    @classmethod
    def create(cls, *args, **kwargs):
        return cls.to_chat_completion(*args, **kwargs).create()

    @classmethod
    def call(cls, *args, **kwargs):
        completion = cls.create(*args, **kwargs)
        return completion.call_function(as_message=False)

    @classmethod
    async def map(cls, *map_args: list, **map_kwargs: list):
        """
        Map the AI Model over a sequence of arguments. Runs concurrently.

        Arguments should be provided as if calling the function normally, but
        each argument must be a list. The function is called once for each item
        in the list, and the results are returned in a list.

        For example, fn.map([1, 2]) is equivalent to [fn(1), fn(2)].

        fn.map([1, 2], x=['a', 'b']) is equivalent to [fn(1, x='a'), fn(2, x='b')].
        """

        if not map_kwargs:
            tasks = [cls.acall(*a) for a in zip(*map_args)]
        else:
            tasks = [
                cls.acall(*a, **{k: v for k, v in zip(map_kwargs.keys(), kw)})
                for a, kw in zip(zip(*map_args), zip(*map_kwargs.values()))
            ]
        return await asyncio.gather(*tasks)

    @classmethod
    async def acreate(cls, *args, **kwargs):
        return await cls.to_chat_completion(*args, **kwargs).acreate()

    @classmethod
    async def acall(cls, *args, **kwargs):
        completion = await cls.acreate(*args, **kwargs)
        return completion.call_function(as_message=False)


ai_model = AIModel.as_decorator
