"""Module for string utilities."""

import tiktoken

import marvin


def tokenize(text: str, model: str = None) -> list[int]:
    """
    Tokenizes the given text using the specified model.

    Args:
        text (str): The text to tokenize.
        model (str, optional): The model to use for tokenization. If not provided,
                               the default model is used.

    Returns:
        list[int]: The tokenized text as a list of integers.
    """
    if model is None:
        model = marvin.settings.openai.chat.completions.model
    tokenizer = tiktoken.encoding_for_model(model)
    return tokenizer.encode(text)


def detokenize(tokens: list[int], model: str = None) -> str:
    """
    Detokenizes the given tokens using the specified model.

    Args:
        tokens (list[int]): The tokens to detokenize.
        model (str, optional): The model to use for detokenization. If not provided,
                               the default model is used.

    Returns:
        str: The detokenized text.
    """
    if model is None:
        model = marvin.settings.openai.chat.completions.model
    tokenizer = tiktoken.encoding_for_model(model)
    return tokenizer.decode(tokens)


def count_tokens(text: str, model: str = None) -> int:
    """
    Counts the number of tokens in the given text using the specified model.

    Args:
        text (str): The text to count tokens in.
        model (str, optional): The model to use for token counting. If not provided,
                               the default model is used.

    Returns:
        int: The number of tokens in the text.
    """
    return len(tokenize(text, model=model))


def slice_tokens(text: str, n_tokens: int, model: str = None) -> str:
    """
    Slices the given text to the specified number of tokens.

    Args:
        text (str): The text to slice.
        n_tokens (int): The number of tokens to slice the text to.
        model (str, optional): The model to use for token counting. If not provided,
                               the default model is used.

    Returns:
        str: The sliced text.
    """
    tokens = tokenize(text, model=model)
    return detokenize(tokens[:n_tokens], model=model)
