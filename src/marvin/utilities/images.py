import base64
from pathlib import Path
from typing import Union


def image_to_base64(image_path: Union[str, Path]) -> str:
    """
    Converts a local image file to a base64 string.

    Args:
        image_path (Union[str, Path]): The path to the image file. This can be a
            string or a Path object.

    Returns:
        str: The base64 representation of the image.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
