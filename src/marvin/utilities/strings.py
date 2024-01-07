"""Module for string utilities."""

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
