"""Module for string utilities."""

import re
from typing import Sequence

from pydantic_ai.messages import AudioUrl, BinaryContent, ImageUrl, UserContent


def _estimate_string_tokens(content: str | Sequence[UserContent]) -> int:
    if not content:
        return 0
    if isinstance(content, str):
        return len(re.split(r'[\s",.:]+', content.strip()))
    else:  # pragma: no cover
        tokens = 0
        for part in content:
            if isinstance(part, str):
                tokens += len(re.split(r'[\s",.:]+', part.strip()))
            if isinstance(part, (AudioUrl, ImageUrl)):
                tokens += 0
            elif isinstance(part, BinaryContent):
                tokens += len(part.data)
            else:
                tokens += 0
        return tokens


def count_tokens(text: str) -> int:
    """
    Counts the number of tokens in the given text using the specified model.

    Args:
        text (str): The text to count tokens in.
        model (str, optional): The model to use for token counting. If not provided,
                               the default model is used.

    Returns:
        int: The number of tokens in the text.
    """
    return _estimate_string_tokens(text)


def slice_tokens(text: str, n_tokens: int) -> str:
    """
    Slices the given text to the specified number of tokens.

    Args:
        text (str): The text to slice.
        n_tokens (int): The number of tokens to slice the text to.

    Returns:
        str: The sliced text.
    """
    tokens = re.split(r'[\s",.:]+', text.strip())
    if n_tokens >= len(tokens):
        return text
    return " ".join(tokens[:n_tokens])
