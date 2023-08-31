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
from marvin.utilities.async_utils import run_sync

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
    " `{{functions[0].__name__}}` function. \n {% if instructions %} You have been"
    " provided instructions on completing your task: {{instructions}}{% endif %}  \n -"
    " Use provided text to extract / infer any parameters needed by"
    " `{{functions[0].__name__}}`,  including any missing data. \n{% if context_fn"
    " %}You have been provided the following context to perform your task:\n{%for (arg,"
    " value) in context_fn(text).items()%}    - {{ arg }}: {{ value }}\n{% endfor %}{%"
    " endif %}"
)


system_generate_prompt = inspect.cleandoc(
    "The user will provide context as text that you need to parse to generate synthetic"
    " data.\n    - To validate your response, you must call the"
    " `{{functions[0].__name__}}` function.\n    - Use the provided text to generate or"
    " invent any parameters needed by `{{functions[0].__name__}}`, including any"
    " missing data.\n    - It is okay to make up representative data.\n{% if"
    " instructions %}You have been provided instructions on completing your task:"
    " {{instructions}}{% endif %}{% if context_fn %}You have been provided the"
    " following context to perform your task:\n{%for (arg, value) in"
    " context_fn(text).items()%}    - {{ arg }}: {{ value }}\n{% endfor %}{% endif %}"
)

user_prompt = inspect.cleandoc("""\
    The text to parse: {{text}}
    """)


class AIModel(BaseModel):
    def __init__(self, *args, **kwargs):
        instructions = kwargs.pop("instructions_", None)
        if text := next(iter(args), None):
            kwargs.update(self.__class__.call(text, instructions=instructions))
        super().__init__(**kwargs)

    @classmethod
    def as_prompt(
        cls,
        text: str = None,
        *args,
        __schema__=True,
        instructions: Optional[str] = None,
        **kwargs,
    ):
        print(instructions)
        print(getattr(cls, "instructions", None))
        response = {}
        response["functions"] = cls._functions(*args, **kwargs)
        response["function_call"] = cls._function_call(
            *args, __schema__=__schema__, **kwargs
        )
        response["messages"] = cls._messages(
            text=text,
            functions=response["functions"],
            **kwargs,
            **({"instructions": instructions} if instructions else {}),
        )
        if __schema__:
            response["functions"] = response["functions"].schema()
        return response

    @classmethod
    def _messages(cls, **kwargs):
        print(kwargs)
        return [
            {
                "role": role,
                "content": Template(kwargs.get(role, "")).render({**kwargs}).strip(),
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
        system: str = None,
        user: str = user_prompt,
        instructions: str = None,
        context_fn: Optional[Callable[[str], dict]] = default_context,
        mode: Literal["extract", "generate"] = "extract",
        model: Any = None,
        **model_kwargs,
    ):
        if not base_model:
            return functools.partial(
                cls.as_decorator,
                system=system
                or (
                    system_extract_prompt
                    if mode == "extract"
                    else system_generate_prompt
                ),
                user=user or user_prompt,
                model=model,
                instructions=instructions,
                context_fn=context_fn,
                **model_kwargs,
            )
        return type(
            base_model.__name__,
            (cls,),
            {
                **dict(base_model.__dict__),
                "_messages": functools.partial(
                    cls._messages,
                    system=system
                    or (
                        system_extract_prompt
                        if mode == "extract"
                        else system_generate_prompt
                    ),
                    user=user or user_prompt,
                    context_fn=context_fn,
                    instructions=instructions,
                ),
            },
        )

    @classmethod
    def to_chat_completion(
        cls, *args, __schema__=False, instructions: str = None, **kwargs
    ):
        return ChatCompletion(
            **cls.as_prompt(
                *args, __schema__=__schema__, instructions=instructions, **kwargs
            )
        )

    @classmethod
    def create(cls, *args, instructions: str = None, **kwargs):
        return cls.to_chat_completion(
            *args, instructions=instructions, **kwargs
        ).create()

    @classmethod
    def call(cls, *args, instructions: str = None, **kwargs):
        completion = cls.create(*args, instructions=instructions, **kwargs)
        return completion.call_function(as_message=False)

    @classmethod
    async def amap(cls, *map_args: list, **map_kwargs: list) -> list:
        """
        Map the AI Model over a sequence of arguments. Runs concurrently.

        Example:
            >>> await Location.amap(["windy city", "big apple"])
            # [Location(city="Chicago"), Location(city="New York City")]
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
    def map(cls, *map_args: list, **map_kwargs: list):
        """
        Map the AI Model over a sequence of arguments. Runs concurrently.
        """
        return run_sync(cls.amap(*map_args, **map_kwargs))

    @classmethod
    async def acreate(cls, *args, **kwargs):
        return await cls.to_chat_completion(*args, **kwargs).acreate()

    @classmethod
    async def acall(cls, *args, **kwargs):
        completion = await cls.acreate(*args, **kwargs)
        return completion.call_function(as_message=False)


ai_model = AIModel.as_decorator
