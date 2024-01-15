"""Module for string utilities."""
from typing import Union

import tiktoken

import marvin


def tokenize(text: str, model: str = None) -> list[int]:
    if model is None:
        model = marvin.settings.openai.chat.completions.model
    tokenizer = tiktoken.encoding_for_model(model)
    return tokenizer.encode(text)


def detokenize(tokens: list[int], model: str = None) -> str:
    if model is None:
        model = marvin.settings.openai.chat.completions.model
    tokenizer = tiktoken.encoding_for_model(model)
    return tokenizer.decode(tokens)


def count_tokens(text: str) -> int:
    return len(tokenize(text))


def slice_tokens(text: str, n_tokens: int) -> str:
    tokens = tokenize(text)
    return detokenize(tokens[:n_tokens])


def split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: float = None,
    last_chunk_threshold: float = None,
    return_index: bool = False,
) -> Union[str, tuple[str, int]]:
    """
    Split a text into a list of strings. Chunks are split by tokens.

    Args:
        text (str): The text to split.
        chunk_size (int): The number of tokens in each chunk.
        chunk_overlap (float): The fraction of overlap between chunks.
        last_chunk_threshold (float): If the last chunk is less than this fraction of
            the chunk_size, it will be added to the prior chunk
        return_index (bool): If True, return a tuple of (chunk, index) where
            index is the character index of the start of the chunk in the original text.
    """
    if chunk_overlap is None:
        chunk_overlap = 0.1
    if chunk_overlap < 0 or chunk_overlap > 1:
        raise ValueError("chunk_overlap must be between 0 and 1")
    if last_chunk_threshold is None:
        last_chunk_threshold = 0.25

    tokens = tokenize(text)

    chunks = []
    for i in range(0, len(tokens), chunk_size - int(chunk_overlap * chunk_size)):
        chunks.append((tokens[i : i + chunk_size], len(detokenize(tokens[:i]))))

    # if the last chunk is too small, merge it with the previous chunk
    if len(chunks) > 1 and len(chunks[-1][0]) < chunk_size * last_chunk_threshold:
        chunks[-2][0].extend(chunks.pop(-1)[0])

    if return_index:
        return [(detokenize(chunk), index) for chunk, index in chunks]
    else:
        return [detokenize(chunk) for chunk, _ in chunks]
