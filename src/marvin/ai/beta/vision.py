from pathlib import Path
from typing import (
    TypeVar,
    Union,
)

from pydantic import BaseModel

import marvin
import marvin.utilities.tools
from marvin.ai.prompts.vision_prompts import CAPTION_PROMPT
from marvin.client.openai import MarvinClient
from marvin.types import (
    BaseMessage,
    ChatResponse,
    MessageImageURLContent,
    VisionRequest,
)
from marvin.utilities.images import image_to_base64
from marvin.utilities.jinja import Transcript
from marvin.utilities.logging import get_logger

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)

logger = get_logger(__name__)


def generate_llm_response(
    prompt_template: str,
    images: list[Union[str, Path]],
    prompt_kwargs: dict = None,
    model_kwargs: dict = None,
) -> ChatResponse:
    """
    Generates a language model response based on a provided prompt template.

    This function uses a language model to generate a response based on a
    provided prompt template. The function supports additional arguments for the
    prompt and the language model.

    Args:
        prompt_template (str): The template for the prompt.
        images (list[Union[str, Path]]): The images to be
            used in the prompt. Can be either URLs or local paths.
        prompt_kwargs (dict, optional): Additional keyword arguments
            for the prompt. Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments
            for the language model. Defaults to None.

    Returns:
        ChatResponse: The generated response from the language model.
    """
    model_kwargs = model_kwargs or {}
    prompt_kwargs = prompt_kwargs or {}
    messages = Transcript(content=prompt_template).render_to_messages(**prompt_kwargs)

    if images is not None:
        for image in images:
            # if images are local paths, convert them to base64. Otherwise
            # assume they are URLs
            if isinstance(image, Path):
                b64_image = image_to_base64(image)
                url = f"data:image/jpeg;base64,{b64_image}"
            else:
                url = image

            messages.append(
                BaseMessage(
                    role="user",
                    content=[MessageImageURLContent(image_url=dict(url=url))],
                )
            )

    request = VisionRequest(messages=messages, **model_kwargs)
    if marvin.settings.log_verbose:
        logger.debug_kv("Request", request.model_dump_json(indent=2))
    response = MarvinClient().generate_vision(
        **request.model_dump(exclude_none=True, exclude_unset=True)
    )
    if marvin.settings.log_verbose:
        logger.debug_kv("Response", response.model_dump_json(indent=2))
    return ChatResponse(request=request, response=response)


def caption(
    image: Union[str, Path],
    instructions: str = None,
    model_kwargs: dict = None,
) -> str:
    """
    Generates a caption for an image.

    This function uses a language model to generate a caption for an image. The
    function supports additional arguments for the language model.

    Args:
        image (Union[str, Path]): The URL or local path of the
            image to be captioned.
        instructions (str, optional): Specific instructions for
            the caption. Defaults to None.
        model_kwargs (dict, optional): Additional keyword
            arguments for the language model. Defaults to None.

    Returns:
        str: The generated caption.
    """
    model_kwargs = model_kwargs or {}
    response = generate_llm_response(
        prompt_template=CAPTION_PROMPT,
        images=[image],
        prompt_kwargs=dict(instructions=instructions),
        model_kwargs=model_kwargs,
    )
    return response.response.choices[0].message.content
