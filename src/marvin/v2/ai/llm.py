from enum import Enum
from functools import wraps
from inspect import cleandoc as cd
from typing import (
    Any,
    Callable,
    GenericAlias,
    Literal,
    Type,
    TypeVar,
    Union,
    get_origin,
)

from pydantic import BaseModel

import marvin
import marvin.utilities.tools
from marvin._mappings.types import (
    cast_options_to_grammar,
    cast_type_to_options,
)
from marvin.prompts.classifiers import CLASSIFIER_PROMPT_V2
from marvin.prompts.functions import EVALUATE_PROMPT_V2
from marvin.requests import ChatRequest, ChatResponse
from marvin.utilities.jinja import Transcript
from marvin.utilities.python import PythonFunction
from marvin.v2.client import ChatCompletion, MarvinClient

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)


def generate_llm_response(
    prompt_template: str,
    prompt_kwargs: dict = None,
    llm_kwargs: dict = None,
) -> ChatResponse:
    llm_kwargs = llm_kwargs or {}
    prompt_kwargs = prompt_kwargs or {}
    messages = Transcript(content=prompt_template).render_to_messages(**prompt_kwargs)
    request = ChatRequest(messages=messages, **llm_kwargs)
    response = MarvinClient().generate_chat(**request.model_dump())
    tool_outputs = get_tool_outputs(request, response)
    return ChatResponse(request=request, response=response, tool_outputs=tool_outputs)


def get_tool_outputs(request: ChatRequest, response: ChatCompletion) -> list[Any]:
    outputs = []
    tool_calls = response.choices[0].message.tool_calls or []
    for tool_call in tool_calls:
        tool_output = marvin.utilities.tools.call_function_tool(
            tools=request.tools,
            function_name=tool_call.function.name,
            function_arguments_json=tool_call.function.arguments,
        )
        outputs.append(tool_output)
    return outputs


def generate_typed_llm_response(
    type_: Union[GenericAlias, type[T]],
    prompt_template: str,
    prompt_kwargs: dict = None,
    llm_kwargs: dict = None,
) -> T:
    llm_kwargs = llm_kwargs or {}
    prompt_kwargs = prompt_kwargs or {}
    tool = marvin.utilities.tools.tool_from_type(type_)
    tool_choice = tool_choice = {
        "type": "function",
        "function": {"name": tool.function.name},
    }

    llm_kwargs.update(tools=[tool], tool_choice=tool_choice)

    # adding the tool parameters to the context helps GPT-4 pay attention to field
    # descriptions. If they are in the tool signature it often ignores them.
    prompt_kwargs.setdefault("context", {})[
        "FormatResponse tool signature"
    ] = tool.function.parameters

    response = generate_llm_response(
        prompt_template=prompt_template,
        prompt_kwargs=prompt_kwargs,
        llm_kwargs=llm_kwargs,
    )

    return response.tool_outputs[0]


def generate_constrained_llm_response(
    data: str,
    options,
    context: dict = None,
    encoder: Callable[[str], list[int]] = None,
    max_tokens: int = 1,
    llm_kwargs: dict = None,
) -> T:
    llm_kwargs = llm_kwargs or {}
    options = cast_type_to_options(options)
    grammar = cast_options_to_grammar(
        options=options, encoder=encoder, max_tokens=max_tokens
    )
    llm_kwargs.update(grammar.model_dump())
    response = generate_llm_response(
        prompt_template=CLASSIFIER_PROMPT_V2,
        prompt_kwargs=dict(data=data, options=options, context=context),
        llm_kwargs=llm_kwargs,
    )
    return options[int(response.response.choices[0].message.content)]


def evaluate(
    objective: str,
    instructions: str = None,
    context: dict = None,
    response_model: Type[T] = None,
    llm_kwargs: dict = None,
    coda: str = None,
):
    """
    General-purpose function for evaluating a natural language objective, given
    instructions and arbitrary context. A response model can be provided to
    constrain the response to a specific type or set of options.
    """
    context = context or {}

    # depending on the response model, we choose a different strategy. For types
    # (the normal case), we generate a typed LLM response. For
    # lists/enums/literals, we generate a constrained chat response. For
    # strings, we use the response model as an instruction.

    # case when the response model is a list of options e.g. Literal, Enum, or List[str]
    if (
        isinstance(response_model, list)
        or get_origin(response_model) == Literal
        or (isinstance(response_model, type) and issubclass(response_model, Enum))
    ):
        return generate_constrained_llm_response(
            data=objective,
            options=response_model,
            context={"Additional instructions": instructions, **context},
        )

    # case when the response model is a string instruction e.g. "A list of names"
    elif isinstance(response_model, str):
        return generate_typed_llm_response(
            prompt_template=EVALUATE_PROMPT_V2,
            prompt_kwargs=dict(
                objective=objective,
                instructions="\n".join([instructions or "", response_model]),
                context=context,
                coda=coda,
            ),
            llm_kwargs=llm_kwargs,
            type_=str,
        )

    # otherwise treat the response
    else:
        return generate_typed_llm_response(
            prompt_template=EVALUATE_PROMPT_V2,
            prompt_kwargs=dict(
                objective=objective,
                instructions=instructions,
                context=context,
                coda=coda,
            ),
            type_=response_model or str,
            llm_kwargs=llm_kwargs,
        )


def cast(text: str, type_: type, instructions: str = None, llm_kwargs: dict = None):
    """
    Convert text into the provided type.
    """
    return evaluate(
        objective=(
            "Your job is to convert the provided text into a more structured form. This"
            " may require you to reinterpret its content or use inference or deduction."
            " Pay attention to "
        ),
        instructions=instructions,
        response_model=type_,
        context=dict(
            text=text,
            response_model=(
                type_.model_json_schema() if isinstance(type, BaseModel) else type_
            ),
        ),
        llm_kwargs={"temperature": 0} | (llm_kwargs or {}),
    )


def extract(
    text: str, type_: type = str, instructions: str = None, llm_kwargs: dict = None
):
    """
    Extract a list of objects from text that match the provided type(s) or instructions.
    """
    return evaluate(
        objective=(
            """
            What values can you extract from this text that match the provided
            instructions and tool? You are an expert and can use inference when
            necessary.
            """
            # "Read the text and extract any values that match the provided instructions"
            # f' and are compatible with the tool signature.\n\nText:"{text}"'
        ),
        instructions=instructions,
        response_model=list[type_],
        context=dict(text=text),
        llm_kwargs={"temperature": 0} | (llm_kwargs or {}),
    )


def classify(text: str, options, instructions: str = None, llm_kwargs: dict = None):
    """
    Classify text as one of the provided options.
    """
    return evaluate(
        objective="Classify the text as one of the provided options.",
        instructions=instructions,
        response_model=options,
        context=dict(text=text),
        llm_kwargs={"temperature": 0} | (llm_kwargs or {}),
    )


def fn(func: Callable):
    """
    A decorator that converts a Python function into an AI function.

    @fn
    def list_fruit(n:int) -> list[str]:
        '''generates a list of n fruit'''

    list_fruit(3) # ['apple', 'banana', 'orange']
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        model = PythonFunction.from_function_call(func, *args, **kwargs)
        return evaluate(
            objective=cd(
                f"""
                Your job is to generate likely outputs for a Python function
                with the following signature and docstring:
                
                {model.definition}
                
                The user will provide function inputs (if any) and you must
                respond with the most likely result.
                """
            ),
            context={
                "The function definition": model.definition,
                "The function was called with these arguments": model.bound_parameters,
                "Additional context": model.return_value,
            },
            coda=cd(
                f"""
                HUMAN: The function was called with the following inputs:
                {model.bound_parameters}
                
                This context was also provided:
                {model.return_value}
                
                What is its output?
                
                ASSISTANT: the output is """
            ),
            response_model=model.return_annotation,
        )

    return wrapper


class AIModel(BaseModel):
    """
    A Pydantic model that can be instantiated from a natural language string, in
    addition to keyword arguments.
    """

    @classmethod
    def from_text(cls, text: str, llm_kwargs: dict = None, **kwargs) -> "AIModel":
        """Async text constructor"""
        ai_kwargs = cast(text, cls, llm_kwargs=llm_kwargs, **kwargs)
        ai_kwargs.update(kwargs)
        return cls(**ai_kwargs)

    def __init__(self, text: str = None, *, llm_kwargs: dict = None, **kwargs):
        ai_kwargs = kwargs
        if text is not None:
            ai_kwargs = cast(text, type(self), llm_kwargs=llm_kwargs).model_dump()
            ai_kwargs.update(kwargs)
        super().__init__(**ai_kwargs)


def model(
    type_: Union[Type[M], None] = None, llm_kwargs: dict = None
) -> Union[Type[M], Callable[[Type[M]], Type[M]]]:
    """
    Class decorator for instantiating a Pydantic model from a string. Equivalent
    to subclassing AIModel.
    """
    llm_kwargs = llm_kwargs or {}

    def decorator(cls: Type[M]) -> Type[M]:
        class Wrapped(AIModel, cls):
            @wraps(cls.__init__)
            def __init__(self, *args, **kwargs):
                super().__init__(*args, llm_kwargs=llm_kwargs, **kwargs)

        Wrapped.__name__ = cls.__name__
        Wrapped.__doc__ = cls.__doc__
        return Wrapped

    if type_ is not None:
        return decorator(type_)
    return decorator
