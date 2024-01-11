from functools import wraps
from typing import TypeVar

from openai.types.images_response import ImagesResponse

import marvin
from marvin.client.openai import MarvinClient
from marvin.core.prompts.image_prompts import IMAGE_PROMPT
from marvin.requests import ImageRequest
from marvin.utilities.jinja import Environment
from marvin.utilities.logging import get_logger

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


def paint(
    instructions: str = None,
    context: dict = None,
    literal: bool = False,
    model_kwargs: dict = None,
):
    """
    Generates an image from the provided instructions and context.

    By default, the DALLE-3 API modifies prompts to add detail and style. To
    disable this behavior, set `literal=True`.
    """
    response = generate_image(
        prompt_template=IMAGE_PROMPT,
        prompt_kwargs=dict(
            instructions=instructions,
            context=context,
            literal=literal,
        ),
        model_kwargs=model_kwargs,
    )
    return response


def image(fn=None, *, literal=False):
    """
    A decorator that transforms a function's output into an image.

    This decorator takes a function that returns a string, and uses that string
    as instructions to generate an image. The generated image is then returned.

    The decorator can be used with or without parentheses. If used without
    parentheses, the decorated function's output is used as the instructions
    for the image. If used with parentheses, an optional `literal` argument can
    be provided. If `literal` is set to `True`, the function's output is used
    as the literal instructions for the image, without any modifications.

    Args:
        fn (callable, optional): The function to decorate. If `None`, the decorator
            is being used with parentheses, and `fn` will be provided later.
        literal (bool, optional): Whether to use the function's output as the
            literal instructions for the image. Defaults to `False`.

    Returns:
        callable: The decorated function.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            prompt = func(*args, **kwargs)
            if prompt is None:
                raise ValueError(
                    f"Function `{func.__name__}` returned `None`. Please return a"
                    " string to use as instructions for image generation."
                )
            return paint(instructions=prompt, literal=literal)

        return wrapper

    if fn is None:
        return decorator
    else:
        return decorator(fn)
