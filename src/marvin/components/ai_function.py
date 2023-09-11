import inspect
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    ClassVar,
    Literal,
    Optional,
    TypeVar,
    Union,
    overload,
)

from marvin._compat import BaseModel, model_dump
from marvin.core.ChatCompletion import BaseChatCompletion, ChatCompletion
from marvin.messages import Prompt

P = TypeVar("P", bound=BaseModel)
B = TypeVar("B", bound=Prompt)


class BaseAIFunctionPrompt(Prompt):
    """
    System: {%- if objective -%}
        {{objective}}
        {% else %}
        The user will provide context as text that you need to parse into a structured form.
        {% endif %}
        To validate your response, you must call the `{{response_model.__name__}}` function. Use the provided text to
        extract or infer any parameters needed by `{{response_model.__name__}}`, including any missing data.
        {% if instructions %}
            - {{instructions}}
        {% endif %}
        The current time is {{now()}}.
        {% if context and text and response_model %}
            - {{context(text = text, response_model = response_model)}}
        {% endif %}

    Human:  The text to parse: {{text}}
    """  # noqa

    objective: Optional[str] = None
    instructions: Optional[str] = None
    context: Optional[Callable[[str], str]] = None
    text: Optional[str] = None

    def __call__(self: B, text: Optional[str] = None, *args: Any, **kwargs: Any) -> B:
        """
        Creates a new instance of the model with the given text,
        passing and re-rendering any additional arguments into the model.

        :param text: The text to use for the prompt.
        :param instructions: Static instructions to use for the prompt.
        :param context: Dynamic context to use for the prompt.

        The `context` parameter is a callable that takes the text and returns a string,
        this is useful for adding dynamic context to the prompt, like Retrieval
        Augmented Generation (RAG) does.

        TODO: Consider letting context evaluate on the passed params.
        """  # noqa

        extras: dict[str, Any] = model_dump(
            self, exclude={"messages", "prompt"}  # type: ignore
        )
        return self.__class__(**extras | kwargs | {"text": text})


class BaseAIFunction(BaseModel):
    """
    The base class for all AI models. The primary purpose of this class is to

    """

    base_model: ClassVar[Callable[..., Any]] = BaseModel
    prompt_class: ClassVar[type[Prompt]] = BaseAIFunctionPrompt
    prompt: ClassVar[Optional[Prompt]] = None
    chat_completion: ClassVar[BaseChatCompletion]

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> "None":
        if not cls.prompt:
            prompt = cls.prompt_class(response_model=cls)
            cls.prompt = prompt
        super().__init_subclass__(*args, **kwargs)

    def __init__(
        self,
        text: Optional[str] = None,
        *args: Any,
        instructions: Optional[str] = None,
        objective: Optional[str] = None,
        context: Optional[Callable[[str, P], str]] = None,
        **kwargs: Any,
    ):
        if text:
            response = self.chat_completion.create(
                **self.as_prompt(
                    text=text,
                    instructions=instructions,
                    objective=objective,
                    context=context,
                )
            )
            print(response.response)

        super().__init__(**kwargs)

    @classmethod
    def as_prompt(
        cls,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return (cls.prompt and cls.prompt or cls.prompt_class)(
            *args, **kwargs
        ).serialize()

    @overload
    @classmethod
    def as_decorator(
        cls,
        *,
        instructions: Optional[str] = None,
        objective: Optional[str] = None,
        context: Optional[Callable[[str, P], str]] = None,
        functions: Optional[
            list[Union[Callable[..., Any], Callable[..., Any], dict[str, Any]]]
        ] = None,  # noqa
        function_call: Optional[
            Union[Literal["auto"], dict[Literal["name"], str]]
        ] = None,  # noqa
        response_model: Optional[Callable[..., Any]] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> Callable[[Callable[..., Any]], type["BaseAIFunction"]]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls,
        func: Callable[..., Any],
        *,
        instructions: Optional[str] = None,
        objective: Optional[str] = None,
        context: Optional[Callable[[str, P], str]] = None,
        functions: Optional[
            list[Union[Callable[..., Any], Callable[..., Any], dict[str, Any]]]
        ] = None,  # noqa
        function_call: Optional[
            Union[Literal["auto"], dict[Literal["name"], str]]
        ] = None,  # noqa
        response_model: Optional[Callable[..., Any]] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> type["BaseAIFunction"]:
        pass

    @classmethod
    def as_decorator(
        cls,
        func: Optional[Callable[..., Any]] = None,
        *,
        instructions: Optional[str] = None,
        objective: Optional[str] = None,
        context: Optional[Callable[[str, P], str]] = None,
        functions: Optional[
            list[Union[Callable[..., Any], Callable[..., Any], dict[str, Any]]]
        ] = None,  # noqa
        function_call: Optional[
            Union[Literal["auto"], dict[Literal["name"], str]]
        ] = None,  # noqa
        response_model: Optional[Callable[..., Any]] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> Union[
        Callable[[Callable[..., Any]], type["BaseAIFunction"]], type["BaseAIFunction"]
    ]:
        def wrapper(func: Callable[..., Any]) -> type["BaseAIFunction"]:  # noqa
            response = type(
                func.__name__,
                (cls,),
                {
                    **func.__dict__,
                    **{"chat_completion": ChatCompletion(model=model, **model_kwargs)},
                    **{
                        "prompt": cls.prompt_class(
                            functions=functions,
                            function_call=function_call,
                            response_model=response_model or inspect.signature(func).return_annotation,  # type: ignore # noqa
                        )(
                            instructions=instructions,  # type: ignore
                            context=context,  # type: ignore
                            objective=objective,  # type: ignore
                            response_model_name=response_model_name
                            or "FormatResponse",  # noqa
                            response_model_description=response_model_description
                            or (
                                "You must call this function to validate your response."
                            ),
                        )
                    },
                },
            )
            response.__doc__ = func.__doc__
            return response

        if func is not None:
            return wraps(cls.as_decorator)(partial(wrapper, func))()

        def decorator(func: Callable[..., Any]) -> type["BaseAIFunction"]:
            return wraps(cls.as_decorator)(partial(wrapper, func))()

        return decorator


def create_decorator(
    *,
    instructions: Optional[str] = None,
    objective: Optional[str] = None,
    context: Optional[Callable[[str, P], str]] = None,
    functions: Optional[
        list[Union[Callable[..., Any], Callable[..., Any], dict[str, Any]]]
    ] = None,  # noqa
    function_call: Optional[
        Union[Literal["auto"], dict[Literal["name"], str]]
    ] = None,  # noqa
    response_model: Optional[Callable[..., Any]] = None,
    response_model_name: Optional[str] = None,
    response_model_description: Optional[str] = None,
    model: Optional[str] = None,
    **model_kwargs: Any,
) -> Union[
    Callable[[Callable[..., Any]], type["BaseAIFunction"]], type["BaseAIFunction"]
]:
    return partial(BaseAIFunction.as_decorator)(
        instructions=instructions,
        objective=objective,
        context=context,
        functions=functions,
        function_call=function_call,
        response_model=response_model,
        response_model_name=response_model_name,
        response_model_description=response_model_description,
        model=model,
        **model_kwargs,  # type: ignore
    )


ai_fn = create_decorator()


# import inspect
# from typing import Any, Callable, Generic, Optional, ParamSpec, TypeVar

# from pydantic import BaseModel, Field, create_model

# from ..core.ChatCompletion import ChatCompletion, BaseChatCompletion
# from ..core.messages import Prompt, prompt

# T = TypeVar('T', bound = 'BaseAIFunction')
# P = ParamSpec('P')
# U = TypeVar('U')


# def ai_fn_prompt(
#         func: Callable[P, Any],
#         instructions: Optional[str] = None,
#         context: Optional[Callable[P, str]] = None,
#     ) -> Callable[P, Prompt]: # noqa

#     @prompt(ctx = {'func': func, 'inspect': inspect})
#     def wrapper(*args: P.args, **kwargs: P.kwargs) -> inspect.signature(func).return_annotation : # type: ignore # noqa
#         '''
#             ASSISTANT: Your job is to generate likely outputs for a Python function with the following signature and docstring: # noqa
#             {{'def' + inspect.getsource(func).split('def')[1]}}
#             The user will provide function inputs (if any) and you must respond with the most likely result.# noqa
#             {{instructions if instructions}}
#             {{context(*args, **kwargs) if context}}

#             HUMAN: The function was called with the following inputs:
#             {%- set signature = inspect.signature(func) -%}
#             {%- set bind = signature.bind(*args, **kwargs) -%}
#             {%- set bind_with_defaults = bind.apply_defaults() -%}
#             {%- for (param, value) in bind.arguments.items() -%}
#                 - {{ param }}: {{ value }}
#             {% endfor %}
#             What is its output?
#         ''' # noqa
#     return wrapper


# def blackbox(prompt: Prompt) -> Any:
#     return 2

# class BaseAIFunction(BaseModel,  Generic[P, U]):
#     func: Callable[P, U]
#     prompt: Callable[[Callable[P, U]], Callable[P, Prompt]] = prompt # noqa
#     model: BaseChatCompletion = Field(default_factory = ChatCompletion)

#     async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> U:
#         prompt = self.as_prompt(*args, **kwargs)
#         response: U = self.model(prompt) # type: ignore
#         return response

#     def call(self, *args: P.args, **kwargs: P.kwargs) -> U:
#         prompt = self.as_prompt(*args, **kwargs)
#         response: U = self.model.create(prompt).to_model() # type: ignore
#         return response

#     async def acall(self, *args: P.args, **kwargs: P.kwargs) -> U:
#         prompt = self.as_prompt(*args, **kwargs)
#         response: U = (await self.model.acreate(prompt)).to_model() # type: ignore
#         return response

#     def as_prompt(
#         self,
#         *args: P.args,
#         **kwargs: P.kwargs,
#     ) -> Prompt:
#         return prompt(self.func)(*args, **kwargs)

#     def response_model(
#         self,
#         func: Optional[Callable[P, U]] = None,
#     ) -> U:
#         mocked_response: U = None # type: ignore
#         return mocked_response

#     @classmethod
#     def as_decorator(
#         cls: type[T],
#         func: Callable[P, U],
#         model: Optional[str] = None,
#         prompt: Optional[Callable[[Callable[P, U]], Callable[P, Prompt]]] = None,
#         sync: bool = True,
#         **model_kwargs: Any,
#     ) -> T:
#         name = getattr(func, '__name__', None)
#         subclass: type[T] = create_model(
#             f'<{cls.__name__} {name}>',
#             __base__=cls,
#             __call__=cls.call if sync else cls.acall,
#         )
#         return subclass(func = func)

# ai_fn = BaseAIFunction.as_decorator
# AIFunction = BaseAIFunction
