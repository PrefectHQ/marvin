from functools import wraps
from typing import Callable, TypeVar

from openai.types.images_response import ImagesResponse

import marvin
from marvin.client.openai import MarvinClient
from marvin.core.prompts.image_templates import IMAGE_PROMPT
from marvin.requests import ImageRequest
from marvin.utilities.jinja import Environment
from marvin.utilities.logging import get_logger
from marvin.utilities.python import PythonFunction

T = TypeVar("T")

logger = get_logger(__name__)


def generate_image(
    prompt_template: str,
    prompt_kwargs: dict = None,
    model_kwargs: dict = None,
) -> ImagesResponse:
    model_kwargs = model_kwargs or {}
    prompt_kwargs = prompt_kwargs or {}
    prompt = Environment.render(prompt_template, **prompt_kwargs)
    request = ImageRequest(prompt=prompt, **model_kwargs)
    if marvin.settings.log_verbose:
        logger.debug_kv("Request", request.model_dump_json(indent=2))
    response = MarvinClient().generate_image(**request.model_dump())
    if marvin.settings.log_verbose:
        logger.debug_kv("Response", response.model_dump_json(indent=2))

    return response


def paint(instructions: str = None, context: dict = None, model_kwargs: dict = None):
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
        return paint(
            instructions=model.docstring,
            context=dict(
                prompt_source="function call",
                **model.model_dump(
                    include={"definition", "bound_parameters", "name", "return_value"}
                ),
            ),
        )

    return wrapper
