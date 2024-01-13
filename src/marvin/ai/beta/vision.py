import inspect
from enum import Enum
from pathlib import Path
from typing import (
    TypeVar,
    Union,
)

from pydantic import BaseModel

import marvin
import marvin.utilities.tools
from marvin.ai.prompts.vision_prompts import (
    CAPTION_PROMPT,
)
from marvin.ai.text import EjectRequest
from marvin.client.openai import MarvinClient
from marvin.types import (
    BaseMessage,
    ChatResponse,
    MessageImageURLContent,
    VisionRequest,
)
from marvin.utilities.context import ctx
from marvin.utilities.images import image_to_base64
from marvin.utilities.jinja import Environment, Transcript
from marvin.utilities.logging import get_logger

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)

logger = get_logger(__name__)


def generate_vision_response(
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
    response = generate_vision_response(
        prompt_template=CAPTION_PROMPT,
        images=[image],
        prompt_kwargs=dict(instructions=instructions),
        model_kwargs=model_kwargs,
    )
    return response.response.choices[0].message.content


def _two_step_vision_response(
    images: list[Union[str, Path]],
    objective: str,
    model_kwargs: dict = None,
):
    """
    Helper function that uses a vision model to process images in a way that
    helps with other, more complex text processing.
    """

    if not isinstance(images, list):
        images = [images]

    vision_template = inspect.cleandoc(
        """
        You are partnering with another AI to complete an objective. The
        objective is written below EXACTLY as it will be shown to the other AI.
        However, the other AI can not process images. YOUR job is to examine
        these images and produce a succinct response that contains any
        image-based information relevant to the objective. You should take all
        other aspects of the objective into account, but your only
        responsibility is to translate the images into relevant data.
        
        Here is the objective, verbatim:
        
        ```
        {{ objective }}
        ```
        
        """
    )

    rendered_vision = Environment.render(vision_template, objective=objective)

    response = generate_vision_response(
        images=images,
        prompt_template=rendered_vision,
        model_kwargs=model_kwargs,
    )

    return response.response.choices[0].message.content


def cast_vision(
    images: str,
    target: type[T],
    data: str = None,
    instructions: str = None,
    vision_model_kwargs: dict = None,
    llm_model_kwargs: dict = None,
) -> T:
    """
    Converts the input data into the specified type using a vision model.

    This function uses a vision model and a language model to convert the input
    data into a specified type. The conversion process can be guided by specific
    instructions. The function also supports additional arguments for both models.

    Args:
        images (list[Union[str, Path]]): The images to be processed.
        data (str): The data to be converted.
        target (type): The type to convert the data into.
        instructions (str, optional): Specific instructions for the conversion.
            Defaults to None.
        vision_model_kwargs (dict, optional): Additional keyword arguments for
            the vision model. Defaults to None.
        llm_model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.

    Returns:
        T: The converted data of the specified type.
    """
    with ctx(eject_request=True):
        try:
            marvin.cast(
                data=data,
                target=target,
                instructions=instructions,
                model_kwargs=llm_model_kwargs,
            )
        except EjectRequest as e:
            objective = "\n\n".join([m.content for m in e.request.messages])

    response = _two_step_vision_response(
        images=images,
        objective=objective,
        model_kwargs=vision_model_kwargs,
    )

    return marvin.cast(
        data=f"{response}\n\n{data if data else ''}",
        target=target,
        instructions=instructions,
        model_kwargs=llm_model_kwargs,
    )


def extract_vision(
    images: str,
    target: type[T],
    data: str = None,
    instructions: str = None,
    vision_model_kwargs: dict = None,
    llm_model_kwargs: dict = None,
) -> T:
    """
    Extracts information from the provided images using a vision model.

    This function uses a vision model and a language model to extract information
    from the provided images. The extraction process can be guided by specific
    instructions. The function also supports additional arguments for both models.

    Args:
        images (Union[Union[str, Path], list[Union[str, Path]]]): The images from
            which to extract information. This can be a single image (URL or local path)
            or a list of images.
        data (str, optional): Additional data for the extraction. Defaults to None.
        instructions (str, optional): Specific instructions for the extraction.
            Defaults to None.
        vision_model_kwargs (dict, optional): Additional keyword arguments for
            the vision model. Defaults to None.
        llm_model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.

    Returns:
        str: The extracted information from the images.
    """
    with ctx(eject_request=True):
        try:
            marvin.extract(
                data=data,
                target=target,
                instructions=instructions,
                model_kwargs=llm_model_kwargs,
            )
        except EjectRequest as e:
            objective = "\n\n".join([m.content for m in e.request.messages])

    response = _two_step_vision_response(
        images=images,
        objective=objective,
        model_kwargs=vision_model_kwargs,
    )

    return marvin.extract(
        data=f"{response}\n\n{data if data else ''}",
        target=target,
        instructions=instructions,
        model_kwargs=llm_model_kwargs,
    )


def classify_vision(
    images: Union[Union[str, Path], list[Union[str, Path]]],
    labels: Union[Enum, list[T], type],
    data: str = None,
    instructions: str = None,
    vision_model_kwargs: dict = None,
    llm_model_kwargs: dict = None,
) -> T:
    """
    Classifies the provided images based on the provided labels.

    This function uses a vision model and a language model with a logit bias to
    classify the images. The logit bias constrains the language model's response
    to a single token, making this function highly efficient for classification
    tasks. The function will always return one of the provided labels.

    Args:
        images (Union[Union[str, Path], list[Union[str, Path]]]): The images to be
            classified. This can be a single image (URL or local path) or a list of images.
        labels (Union[Enum, list[T], type]): The labels to classify the images into.
        data (str, optional): Additional data for the classification. Defaults to None.
        instructions (str, optional): Specific instructions for the
            classification. Defaults to None.
        vision_model_kwargs (dict, optional): Additional keyword arguments for
            the vision model. Defaults to None.
        llm_model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.

    Returns:
        T: The label that the images were classified into.
    """

    with ctx(eject_request=True):
        try:
            marvin.classify(
                data=data,
                labels=labels,
                instructions=instructions,
                model_kwargs=llm_model_kwargs,
            )
        except EjectRequest as e:
            objective = "\n\n".join([m.content for m in e.request.messages])

    response = _two_step_vision_response(
        images=images,
        objective=objective,
        model_kwargs=vision_model_kwargs,
    )

    return marvin.classify(
        data=f"{response}\n\n{data if data else ''}",
        labels=labels,
        instructions=instructions,
        model_kwargs=llm_model_kwargs,
    )
