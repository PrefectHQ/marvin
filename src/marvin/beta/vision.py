"""
This model contains tools for working with the vision API, including
vision-enhanced versions of `cast`, `extract`, and `classify`.
"""

import inspect
from enum import Enum
from pathlib import Path
from typing import Callable, Coroutine, Optional, TypeVar, Union

from pydantic import BaseModel

import marvin
import marvin.utilities.tools
from marvin.ai.prompts.vision_prompts import CAPTION_PROMPT
from marvin.ai.text import EjectRequest
from marvin.client.openai import AsyncMarvinClient
from marvin.types import (
    BaseMessage,
    ChatResponse,
    MessageImageURLContent,
    VisionRequest,
)
from marvin.utilities.asyncio import run_sync
from marvin.utilities.context import ctx
from marvin.utilities.images import image_to_base64
from marvin.utilities.jinja import Transcript
from marvin.utilities.logging import get_logger
from marvin.utilities.mapping import map_async

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)

logger = get_logger(__name__)


class Image(BaseModel):
    url: str

    def __init__(self, path_or_url: Union[str, Path], **kwargs):
        if isinstance(path_or_url, str) and Path(path_or_url).exists():
            path_or_url = Path(path_or_url)

        if isinstance(path_or_url, Path):
            b64_image = image_to_base64(path_or_url)
            url = f"data:image/jpeg;base64,{b64_image}"
        else:
            url = path_or_url
        super().__init__(url=url, **kwargs)

    def to_message_content(self) -> MessageImageURLContent:
        return MessageImageURLContent(image_url=dict(url=self.url))


async def generate_vision_response(
    images: list[Image],
    prompt_template: str,
    prompt_kwargs: dict = None,
    model_kwargs: dict = None,
) -> ChatResponse:
    """
    Generates a language model response based on a provided prompt template and images.

    Args:
        images (list[Image]): Images used in the prompt, either URLs or local paths.
        prompt_template (str): Template for the language model prompt.
        prompt_kwargs (dict, optional): Keyword arguments for the prompt.
        model_kwargs (dict, optional): Keyword arguments for the language model.

    Returns:
        ChatResponse: Response from the language model.
    """
    model_kwargs = model_kwargs or {}
    prompt_kwargs = prompt_kwargs or {}
    messages = Transcript(content=prompt_template).render_to_messages(**prompt_kwargs)

    if images is not None:
        content = []
        for image in images:
            if not isinstance(image, Image):
                image = Image(image)
            content.append(image.to_message_content())
        messages.append(BaseMessage(role="user", content=content))

    request = VisionRequest(messages=messages, **model_kwargs)
    if marvin.settings.log_verbose:
        logger.debug_kv("Request", request.model_dump_json(indent=2))
    response = await AsyncMarvinClient().generate_vision(
        **request.model_dump(exclude_none=True, exclude_unset=True)
    )
    if marvin.settings.log_verbose:
        logger.debug_kv("Response", response.model_dump_json(indent=2))
    return ChatResponse(request=request, response=response)


async def _two_step_vision_response(
    data: Union[str, Image],
    images: list[Image],
    marvin_call: Union[Callable, Coroutine],
    vision_model_kwargs: dict = None,
):
    """
    Helper function to process images and data for various Marvin operations.

    Args:
        data (Union[str, None]): Additional data for processing.
        images (list[Image]): Images to be processed.
        marvin_call (Union[Callable, Coroutine]): A function that takes a single
            argument, data, encapsulating the specific Marvin function call.
        vision_model_kwargs (dict, optional): Arguments for the vision model.

    Returns:
        T: Processed data of the specified type.
    """
    images = images or []

    if not isinstance(images, list):
        images = [images]

    if not images and not isinstance(data, Image):
        if inspect.iscoroutinefunction(marvin_call):
            return await marvin_call(data)
        else:
            return marvin_call(data)

    if isinstance(data, Image):
        images.append(data)
        data = None

    # a little hacky but this lets us eject the full prompt no matter what logic
    # is used in the marvin_call function
    with ctx(eject_request=True):
        try:
            if inspect.iscoroutinefunction(marvin_call):
                await marvin_call(data)
            else:
                marvin_call(data)
            raise ValueError("Expected to raise EjectRequest")
        except EjectRequest as e:
            objective = "\n\n".join([m.content for m in e.request.messages])

    prompt = inspect.cleandoc(
        """
        You are partnering with another AI to complete an objective. The
        objective is written below EXACTLY as it will be shown to the other AI.
        However, the other AI can not process images. YOUR job is to examine
        these images and produce a succinct response that contains any
        image-based information relevant to the objective. You should take all
        other aspects of the objective into account, but your only
        responsibility is to translate the images into relevant data. 
        
        Do not tell the other AI what to do or return, as it will get confused.
        Just return a description of the image that contains any detail the
        other AI can use to generate its own response. You may be as succinct as
        possible.
        
        Here is the objective, verbatim:
        
        ```{objective}```
        """
    ).format(objective=objective)

    response = await generate_vision_response(
        images=images,
        prompt_template=prompt,
        model_kwargs=vision_model_kwargs,
    )

    vision_response = response.response.choices[0].message.content

    msg = (
        f"## Text data\n\n{data}\n\n## Image data analysis\n\nThe data also include an"
        " image. Another AI processed it and determined the"
        f" following:\n\n{vision_response}"
    )
    if inspect.iscoroutinefunction(marvin_call):
        return await marvin_call(msg)
    else:
        return marvin_call(msg)


async def caption_async(
    image: Union[str, Path, Image],
    instructions: str = None,
    model_kwargs: dict = None,
) -> str:
    """
    Generates a caption for an image using a language model.

    Args:
        image (Union[str, Path, Image]): URL or local path of the image.
        instructions (str, optional): Instructions for the caption generation.
        model_kwargs (dict, optional): Additional arguments for the language model.

    Returns:
        str: Generated caption.
    """
    model_kwargs = model_kwargs or {}
    response = await generate_vision_response(
        prompt_template=CAPTION_PROMPT,
        images=[image],
        prompt_kwargs=dict(instructions=instructions),
        model_kwargs=model_kwargs,
    )
    return response.response.choices[0].message.content


async def cast_async(
    data: Union[str, Image],
    target: type[T],
    instructions: str = None,
    images: list[Image] = None,
    vision_model_kwargs: dict = None,
    model_kwargs: dict = None,
) -> T:
    """
    Converts the input data into the specified type using a vision model.

    This function uses a vision model and a language model to convert the input
    data into a specified type. The conversion process can be guided by specific
    instructions. The function also supports additional arguments for both models.

    Args:
        images (list[Image]): The images to be processed.
        data (str): The data to be converted.
        target (type): The type to convert the data into.
        instructions (str, optional): Specific instructions for the conversion.
            Defaults to None.
        vision_model_kwargs (dict, optional): Additional keyword arguments for
            the vision model. Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.

    Returns:
        T: The converted data of the specified type.
    """

    async def marvin_call(x):
        return await marvin.cast_async(
            data=x,
            target=target,
            instructions=instructions,
            model_kwargs=model_kwargs,
        )

    return await _two_step_vision_response(
        data=data,
        images=images,
        marvin_call=marvin_call,
        vision_model_kwargs=vision_model_kwargs,
    )


async def extract_async(
    data: Union[str, Image],
    target: type[T],
    instructions: str = None,
    images: list[Image] = None,
    vision_model_kwargs: dict = None,
    model_kwargs: dict = None,
) -> T:
    """
    Extracts information from provided data and/or images using a vision model.

    Args:
        data (Union[str, Image]): Data or an image for information extraction.
        target (type[T]): The type to extract the data into.
        instructions (str, optional): Instructions for extraction.
        images (list[Union[str, Path]], optional): Additional images for extraction.
        vision_model_kwargs (dict, optional): Arguments for the vision model.
        model_kwargs (dict, optional): Arguments for the language model.

    Returns:
        T: Extracted data of the specified type.
    """

    async def marvin_call(x):
        return await marvin.extract_async(
            data=x,
            target=target,
            instructions=instructions,
            model_kwargs=model_kwargs,
        )

    return await _two_step_vision_response(
        data=data,
        images=images,
        marvin_call=marvin_call,
        vision_model_kwargs=vision_model_kwargs,
    )


async def classify_async(
    data: Union[str, Image],
    labels: Union[Enum, list[T], type],
    images: Union[Union[str, Path], list[Union[str, Path]]] = None,
    instructions: str = None,
    vision_model_kwargs: dict = None,
    model_kwargs: dict = None,
) -> T:
    """
    Classifies provided data and/or images into one of the specified labels.
    Args:
        data (Union[str, Image]): Data or an image for classification.
        labels (Union[Enum, list[T], type]): Labels to classify into.
        images (Union[Union[str, Path], list[Union[str, Path]]], optional): Additional images for classification.
        instructions (str, optional): Instructions for the classification.
        vision_model_kwargs (dict, optional): Arguments for the vision model.
        model_kwargs (dict, optional): Arguments for the language model.

    Returns:
        T: Label that the data/images were classified into.
    """

    async def marvin_call(x):
        return await marvin.classify_async(
            data=x,
            labels=labels,
            instructions=instructions,
            model_kwargs=model_kwargs,
        )

    return await _two_step_vision_response(
        data=data,
        images=images,
        marvin_call=marvin_call,
        vision_model_kwargs=vision_model_kwargs,
    )


# Sync versions of the above functions


def caption(
    image: Union[str, Path, Image],
    instructions: str = None,
    model_kwargs: dict = None,
) -> str:
    """
    Generates a caption for an image using a language model synchronously.

    Args:
        image (Union[str, Path, Image]): URL or local path of the image.
        instructions (str, optional): Instructions for the caption generation.
        model_kwargs (dict, optional): Additional arguments for the language model.

    Returns:
        str: Generated caption.
    """
    return run_sync(
        caption_async(
            image=image,
            instructions=instructions,
            model_kwargs=model_kwargs,
        )
    )


def cast(
    data: Union[str, Image],
    target: type[T],
    instructions: str = None,
    images: list[Image] = None,
    vision_model_kwargs: dict = None,
    model_kwargs: dict = None,
) -> T:
    """
    Converts the input data into the specified type using a vision model synchronously.

    Args:
        data (Union[str, Image]): The data to be converted.
        target (type[T]): The type to convert the data into.
        instructions (str, optional): Specific instructions for the conversion.
        images (list[Image], optional): The images to be processed.
        vision_model_kwargs (dict, optional): Additional keyword arguments for the vision model.
        model_kwargs (dict, optional): Additional keyword arguments for the language model.

    Returns:
        T: The converted data of the specified type.
    """
    return run_sync(
        cast_async(
            data=data,
            target=target,
            instructions=instructions,
            images=images,
            vision_model_kwargs=vision_model_kwargs,
            model_kwargs=model_kwargs,
        )
    )


def extract(
    data: Union[str, Image],
    target: type[T],
    instructions: str = None,
    images: list[Image] = None,
    vision_model_kwargs: dict = None,
    model_kwargs: dict = None,
) -> T:
    """
    Extracts information from provided data and/or images using a vision model synchronously.

    Args:
        data (Union[str, Image]): Data or an image for information extraction.
        target (type[T]): The type to extract the data into.
        instructions (str, optional): Instructions for extraction.
        images (list[Image], optional): Additional images for extraction.
        vision_model_kwargs (dict, optional): Arguments for the vision model.
        model_kwargs (dict, optional): Arguments for the language model.

    Returns:
        T: Extracted data of the specified type.
    """
    return run_sync(
        extract_async(
            data=data,
            target=target,
            instructions=instructions,
            images=images,
            vision_model_kwargs=vision_model_kwargs,
            model_kwargs=model_kwargs,
        )
    )


def classify(
    data: Union[str, Image],
    labels: Union[Enum, list[T], type],
    images: Union[Image, list[Image]] = None,
    instructions: str = None,
    vision_model_kwargs: dict = None,
    model_kwargs: dict = None,
) -> T:
    """
    Classifies provided data and/or images into one of the specified labels synchronously.

    Args:
        data (Union[str, Image]): Data or an image for classification.
        labels (Union[Enum, list[T], type]): Labels to classify into.
        images (Union[Image, list[Image]], optional): Additional images for classification.
        instructions (str, optional): Instructions for the classification.
        vision_model_kwargs (dict, optional): Arguments for the vision model.
        model_kwargs (dict, optional): Arguments for the language model.

    Returns:
        T: Label that the data/images were classified into.
    """
    return run_sync(
        classify_async(
            data=data,
            labels=labels,
            images=images,
            instructions=instructions,
            vision_model_kwargs=vision_model_kwargs,
            model_kwargs=model_kwargs,
        )
    )


# --- Mapping
async def classify_async_map(
    data: list[Union[str, Image]],
    labels: Union[Enum, list[T], type],
    instructions: Optional[str] = None,
    model_kwargs: Optional[dict] = None,
) -> list[T]:
    return await map_async(
        fn=classify_async,
        map_kwargs=dict(data=data),
        unmapped_kwargs=dict(
            labels=labels,
            instructions=instructions,
            model_kwargs=model_kwargs,
        ),
    )


def classify_map(
    data: list[Union[str, Image]],
    labels: Union[Enum, list[T], type],
    instructions: Optional[str] = None,
    model_kwargs: Optional[dict] = None,
) -> list[T]:
    return run_sync(
        classify_async_map(
            data=data,
            labels=labels,
            instructions=instructions,
            model_kwargs=model_kwargs,
        )
    )


async def cast_async_map(
    data: list[Union[str, Image]],
    target: type[T],
    instructions: Optional[str] = None,
    images: list[list[Image]] = None,
    model_kwargs: Optional[dict] = None,
) -> list[T]:
    return await map_async(
        fn=cast_async,
        map_kwargs=dict(data=data, images=images or []),
        unmapped_kwargs=dict(
            target=target,
            instructions=instructions,
            model_kwargs=model_kwargs,
        ),
    )


def cast_map(
    data: list[Union[str, Image]],
    target: type[T],
    instructions: Optional[str] = None,
    images: list[list[Image]] = None,
    model_kwargs: Optional[dict] = None,
) -> list[T]:
    return run_sync(
        cast_async_map(
            data=data,
            images=images,
            target=target,
            instructions=instructions,
            model_kwargs=model_kwargs,
        )
    )


async def extract_async_map(
    data: list[Union[str, Image]],
    target: Optional[type[T]] = None,
    instructions: Optional[str] = None,
    model_kwargs: Optional[dict] = None,
) -> list[list[T]]:
    return await map_async(
        fn=extract_async,
        map_kwargs=dict(data=data),
        unmapped_kwargs=dict(
            target=target,
            instructions=instructions,
            model_kwargs=model_kwargs,
        ),
    )


def extract_map(
    data: list[Union[str, Image]],
    target: Optional[type[T]] = None,
    instructions: Optional[str] = None,
    model_kwargs: Optional[dict] = None,
) -> list[list[T]]:
    return run_sync(
        extract_async_map(
            data=data,
            target=target,
            instructions=instructions,
            model_kwargs=model_kwargs,
        )
    )


cast_async.map = cast_async_map
cast.map = cast_map
classify_async.map = classify_async_map
classify.map = classify_map
extract_async.map = extract_async_map
extract.map = extract_map
