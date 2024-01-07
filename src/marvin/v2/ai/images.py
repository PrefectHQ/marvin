from functools import wraps
from typing import Callable, TypeVar

from openai.types.images_response import ImagesResponse

from marvin.requests import ImageRequest
from marvin.utilities.jinja import Environment
from marvin.utilities.python import PythonFunction
from marvin.v2.ai.prompt_templates import IMAGE_PROMPT
from marvin.v2.client import MarvinClient

T = TypeVar("T")


def generate_image(
    prompt_template: str,
    prompt_kwargs: dict = None,
    model_kwargs: dict = None,
) -> ImagesResponse:
    prompt_kwargs = prompt_kwargs or {}
    model_kwargs = model_kwargs or {}
    prompt = Environment.render(prompt_template, **prompt_kwargs)
    request = ImageRequest(prompt=prompt, **model_kwargs)
    response = MarvinClient().generate_image(**request.model_dump())
    return response


def imagine(instructions: str = None, context: dict = None, model_kwargs: dict = None):
    response = generate_image(
        prompt_template=IMAGE_PROMPT,
        prompt_kwargs=dict(
            instructions=instructions,
            context=context,
        ),
        model_kwargs=model_kwargs,
    )
    return response


def image(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        model = PythonFunction.from_function_call(fn, *args, **kwargs)
        return imagine(
            instructions=model.docstring,
            context=model.model_dump(
                include={"bound_parameters", "parameters", "name", "return_value"}
            ),
        )

    return wrapper
