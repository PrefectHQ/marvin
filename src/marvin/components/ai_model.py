from functools import partial
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Optional,
    Type,
    Union,
    overload,
)

from marvin._compat import BaseModel, cast_to_model
from marvin.core.ChatCompletion import BaseChatCompletion, ChatCompletion
from marvin.messages import BasePrompt, prompt
from marvin.types import ParamSpec

P = ParamSpec("P")


def ai_model_prompt(
    model: type,
    response_model_name: Optional[str] = "FormatResponse",
    response_model_description: Optional[
        str
    ] = "You must call this function to validate your response.",  # noqa
) -> Callable[P, "BasePrompt"]:
    response_model: type[BaseModel] = cast_to_model(
        model, name=response_model_name, description=response_model_description
    )

    @prompt(response_model=response_model)
    def wrapper(
        text: str = "",
        *,
        objective: Optional[str] = None,
        instructions: Optional[str] = None,
        context: Optional[Callable[..., str]] = None,
    ) -> None:
        """
        System:
        {%- if objective %}
        {{objective}}
        {%- else %}
        The user will provide context as text that you need to parse into a structured form.
        {%- endif %}
        {%- set model_name = response_model.__name__ %}

        To validate your response, you must call the `{{model_name}}` function.
        Use the provided text to extract or infer any parameters needed by `{{model_name}}`, including any missing data.
        {{- instructions if instructions }}
        The current time is {{now()}}.
        {{ context(text) if context and text }}

        Human: The text to parse: {{text}}
        """  # noqa

    return wrapper


class BaseAIModel(BaseModel, Generic[P]):
    ChatCompletion: ClassVar[BaseChatCompletion] = ChatCompletion()
    objective: ClassVar[Optional[str]] = None
    instructions: ClassVar[Optional[str]] = None
    context: ClassVar[Optional[Callable[..., str]]] = None

    def __init__(
        self,
        text: Optional[str] = "",
        _objective: Optional[str] = None,
        _instuctions: Optional[str] = None,
        _context: Optional[Callable[..., str]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        A modified version of the constructor that accepts a single
        positional `text` argument.
        - If no `text` is provided, the constructor falls back to the default
        behavior of the `BaseModel` constructor, which does not accept a
        `text` argument. So you can still use the `BaseAIModel` class as a
        base class for your own models.
        - If `text` is provided, it is passed to the `prompt` method of the
        model, which returns a `ChatCompletion` object. The `ChatCompletion`
        performs the actual API call to the model, and returns the result,
        which is spread into the `BaseModel` constructor as keyword arguments.

        :param text: The text to parse.
        :param _objective: The objective of the prompt.
        :param _instructions: The instructions for the prompt.
        :param _context: The context for the prompt, which is a function that
        accepts the `text` argument and returns a string. Helpful for
        Retrieval Augmented Generation (RAG) models.
        """
        super().__init__(**kwargs)

    @classmethod
    def prompt(cls) -> Callable[P, "BasePrompt"]:
        """
        A decorator that adds a `prompt` method to the class.

        If you want to customize the prompt, you can subclass `BaseAIModel`
        and override this method.
        """
        return ai_model_prompt(cls)

    @classmethod
    def as_prompt(cls, *args: P.args, **kwargs: P.kwargs) -> dict[str, Any]:
        return cls.prompt()(*args, **kwargs).serialize()

    @classmethod
    def call(cls, *args: P.args, **kwargs: P.kwargs) -> Any:
        """
        A convenience method that calls the `ChatCompletion` object directly.
        """
        return cls.ChatCompletion.create(**cls.as_prompt(*args, **kwargs))


@overload
def ai_model(
    *,
    prompt: Optional[Callable[..., Callable[..., "BasePrompt"]]] = None,
    objective: Optional[str] = None,
    instructions: Optional[str] = None,
    context: Optional[Callable[..., str]] = None,
    model: Optional[str] = None,
    **model_kwargs: Any,
) -> Callable[..., Callable[..., Any]]:
    ...


@overload
def ai_model(
    base_model: Type[BaseModel],
    *,
    prompt: Optional[Callable[..., Callable[P, "BasePrompt"]]] = None,
    objective: Optional[str] = None,
    instructions: Optional[str] = None,
    context: Optional[Callable[..., str]] = None,
    model: Optional[str] = None,
    **model_kwargs: Any,
) -> Type[BaseAIModel[P]]:
    ...


def ai_model(
    base_model: Optional[Type[BaseModel]] = None,
    prompt: Optional[Callable[..., Callable[P, "BasePrompt"]]] = None,
    objective: Optional[str] = None,
    instructions: Optional[str] = None,
    context: Optional[Callable[..., str]] = None,
    model: Optional[str] = None,
    **model_kwargs: Any,
) -> Union[Callable[..., Callable[..., Any]], Type[BaseAIModel[P]]]:
    if base_model is None:
        return partial(ai_model, prompt=prompt)
    return type(
        base_model.__name__,
        (BaseAIModel,),
        {
            "ChatCompletion": ChatCompletion(model, **model_kwargs),
            "objective": objective,
            "instructions": instructions,
            "context": context,
            **base_model.__dict__,
        },
    )


# @ai_model(instruction='Please provide your name.')
# class Person(BaseModel):
#     name: str

# Person
