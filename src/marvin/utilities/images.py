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


def base64_to_image(base64_str: str, output_path: Union[str, Path]) -> None:
    """
    Converts a base64 string to a local image file.

    Args:
        base64_str (str): The base64 string representation of the image.
        output_path (Union[str, Path]): The path to the output image file. This can be a
            string or a Path object.

    Returns:
        None
    """
    image_data = base64.b64decode(base64_str)

    # Cast to Path for more utility functions
    output_path = Path(output_path)

    # Ensure the parent directory of the output path exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("wb") as output_file:
        output_file.write(image_data)
