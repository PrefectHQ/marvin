import asyncio
import inspect
from enum import Enum, EnumMeta
from typing import Callable, Literal, Optional

from jinja2 import Template
from pydantic import create_model
from pydantic.fields import FieldInfo

from marvin.core.ChatCompletion import ChatCompletion
from marvin.types import Function, FunctionRegistry
from marvin.utilities.async_utils import run_sync

system_prompt = inspect.cleandoc("""\
    You are an expert classifier that always chooses correctly.
    {% if enum_class_docstring %}    
    Your classification task is: {{ enum_class_docstring }}
    {% endif %}
    {% if instructions %}
    Your instructions are: {{ instructions }}
    {% endif %}
    The user will provide context through text, you will use your expertise 
    to choose the best option below based on it:
    {% for option in options %}
        {{ loop.index }}. {{ value_getter(option) }}
    {% endfor %}
    {% if context_fn %}
    You have been provided the following context to perform your task:\n
    {%for (arg, value) in context_fn(value).items()%}
        - {{ arg }}: {{ value }}\n
    {% endfor %}
    {% endif %}\
    """)

user_prompt = inspect.cleandoc("""{{ value }}""")


class AIEnumMeta(EnumMeta):
    """
    A metaclass for the AIEnum class: extends the functionality of EnumMeta
    the metaclass for Python's built-in Enum class, allows additional params to be
    passed when creating an enum. These parameters are used to customize the behavior
    of the AI classifier.
    """

    def __call__(
        cls,
        value,
        names=None,
        *values,
        module=None,
        qualname=None,
        type=None,
        start=1,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        value_getter: Callable = lambda x: x.name,
        context_fn: Optional[Callable] = None,
        instructions: Optional[str] = None,
        method: Literal["logit_bias", "function"] = "logit_bias",
        model: ChatCompletion = None,
        **kwargs,
    ):
        # If kwargs are provided, handle the missing case
        if kwargs:
            return cls._missing_(
                value,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                value_getter=value_getter,
                context_fn=context_fn,
                instructions=instructions,
                method=method,
                model=model,
                **kwargs,
            )
        else:
            # Call the parent class's __call__ method to create the enum
            enum = super().__call__(
                value,
                names,
                *values,
                module=module,
                qualname=qualname,
                type=type,
                start=start,
            )

            # Set additional attributes for the AI classifier
            setattr(enum, "__system_prompt__", system_prompt)
            setattr(enum, "__user_prompt__", user_prompt)
            setattr(enum, "__model__", model)
            setattr(enum, "__value_getter__", value_getter)
            setattr(enum, "__context_fn__", context_fn)
            setattr(enum, "__instructions__", instructions)
            setattr(enum, "__method__", method)
            return enum


class AIEnum(Enum, metaclass=AIEnumMeta):
    """
    AIEnum is a class that extends Python's built-in Enum class.
    It uses the AIEnumMeta metaclass, which allows additional parameters to be passed
    when creating an enum. These parameters are used to customize the behavior
    of the AI classifier.
    """

    @classmethod
    def prompt(
        cls,
        *args,
        __schema__: bool = True,
        **kwargs,
    ):
        response = {}
        response["messages"] = cls._messages(*args, **kwargs)
        method = kwargs.get("method", cls.__method__)
        if method == "logit_bias":
            response.update({"logit_bias": cls._logit_bias(*args, **kwargs)})
            response.update({"max_tokens": 1})
        else:
            response.update({"functions": cls._functions(*args, **kwargs)})
            response.update(
                {
                    "function_call": cls._function_call(
                        *args, __schema__=__schema__, **kwargs
                    )
                }
            )
            if __schema__:
                response["functions"] = response["functions"].schema()
        return response

    @classmethod
    def _logit_bias(cls, *args, **kwargs):
        return {
            next(iter(cls.__model__.get_tokens(str(i)))): 100
            for i in range(1, len(cls) + 1)
        }

    @classmethod
    def _functions(cls, *args, **kwargs):
        model = create_model(
            "Index", **{"index": (int, FieldInfo(min=1, max=len(cls)))}
        )
        model.__doc__ = cls.__doc__ or "A enumeration of choices."
        return FunctionRegistry([Function.from_model(model)])

    @classmethod
    def _function_call(cls, *args, __schema__=True, **kwargs):
        if __schema__:
            return {"name": cls._functions(*args, **kwargs).schema()[0].get("name")}
        return {"name": cls._functions(*args, **kwargs)[0].__name__}

    @classmethod
    def _messages(
        cls,
        value,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        value_getter: Callable = None,
        instructions: Optional[str] = None,
        method: Literal["logit_bias", "function"] = None,
        context_fn: Optional[Callable] = None,
        **kwargs,
    ):
        """
        Generate the messages to be used as prompts for the AI classifier. The messages
        are created based on the system and user templates provided.
        """
        # don't pass the generic enum docstring through
        if cls.__doc__ != "An enumeration.":
            pass
        instructions = instructions or cls.__instructions__
        system_prompt = system_prompt or cls.__system_prompt__
        user_prompt = user_prompt or cls.__user_prompt__
        value_getter = value_getter or cls.__value_getter__
        context_fn = context_fn or cls.__context_fn__
        method = method or cls.__method__

        return [
            {
                "role": "system",
                "content": (
                    Template(system_prompt)
                    .render(
                        value=value,
                        instructions=instructions,
                        options=cls,
                        value_getter=value_getter,
                        context_fn=context_fn,
                        enum_class_docstring=cls.__doc__,
                    )
                    .strip()
                ),
            },
            {
                "role": "user",
                "content": (
                    Template(user_prompt)
                    .render(
                        value=value,
                        value_getter=value_getter,
                        context_fn=context_fn,
                    )
                    .strip()
                ),
            },
        ]

    @classmethod
    def _missing_(cls, *args, **kwargs):
        return run_sync(cls.__missing_async__(*args, **kwargs))

    @classmethod
    def to_chat_completion(cls, *args, __schema__=False, **kwargs):
        return cls.__model__(**cls.prompt(*args, __schema__=__schema__, **kwargs))

    @classmethod
    def create(cls, *args, **kwargs):
        return cls.to_chat_completion(*args, **kwargs).create()

    @classmethod
    def call(cls, *args, **kwargs):
        completion = cls.create(*args, **kwargs)
        if completion.has_function_call():
            index = completion.call_function(as_message=False).index
        else:
            index = completion.choices[0].message.content
        return list(cls)[int(index) - 1]

    @classmethod
    async def acreate(cls, *args, **kwargs):
        return await cls.to_chat_completion(*args, **kwargs).acreate()

    @classmethod
    async def acall(cls, *args, **kwargs):
        completion = await cls.acreate(*args, **kwargs)
        if completion.has_function_call():
            index = completion.call_function(as_message=False).index
        else:
            index = completion.choices[0].message.content
        return list(cls)[int(index) - 1]

    @classmethod
    async def __missing_async__(cls, *args, **kwargs):
        """
        Handle the case where a value is not found in the enum. This method is a part
        of Python's Enum API and is called when an attempt is made to access an enum
        member that does not exist.
        """
        return await cls.acall(*args, **kwargs)

    @classmethod
    def map(cls, items: list[str], **kwargs):
        """
        Map the classifier over a list of items.
        """
        coros = [cls.__missing_async__(item, **kwargs) for item in items]

        # gather returns a future, but run_sync requires a coroutine
        async def gather_coros():
            return await asyncio.gather(*coros)

        result = run_sync(gather_coros())
        return result


def ai_classifier(
    cls=None,
    model: ChatCompletion = ChatCompletion,
    system_prompt: str = system_prompt,
    user_prompt: str = user_prompt,
    value_getter: Callable = lambda x: x.name,
    context_fn: Optional[Callable] = None,
    instructions: Optional[str] = None,
    method: Literal["logit_bias", "function"] = "logit_bias",
    **model_kwargs,
):
    """
    A decorator that transforms a regular Enum class into an AIEnum class. It adds
    additional attributes and methods to the class that are used to customize the
    behavior of the AI classifier.
    """

    def decorator(enum_class):
        ai_enum_class = AIEnum(
            enum_class.__name__,
            {member.name: member.value for member in enum_class},
            model=model(**model_kwargs),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            value_getter=value_getter,
            context_fn=context_fn,
            instructions=instructions,
            method=method,
        )

        # Preserve the original class's docstring
        ai_enum_class.__doc__ = enum_class.__doc__ or None
        return ai_enum_class

    if cls is None:
        return decorator
    else:
        return decorator(cls)
