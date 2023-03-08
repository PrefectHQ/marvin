import asyncio
import re
from functools import lru_cache
from string import Formatter
from typing import Any, Callable, Mapping, Sequence, Union

import pendulum
import tiktoken
import xxhash
from jinja2 import ChoiceLoader, Environment, StrictUndefined, select_autoescape

import marvin

jinja_env = Environment(
    loader=ChoiceLoader(
        [
            # PackageLoader("marvin", "prompts"),
            # PackageLoader("marvin", "programs"),
        ]
    ),
    autoescape=select_autoescape(default_for_string=False),
    trim_blocks=True,
    lstrip_blocks=True,
    enable_async=True,
    auto_reload=True,
    undefined=StrictUndefined,
)
jinja_env.globals.update(
    zip=zip,
    str=str,
    len=len,
    arun=asyncio.run,
    pendulum=pendulum,
    dt=lambda: pendulum.now("UTC").to_day_datetime_string(),
)


class StrictFormatter(Formatter):
    """A subclass of formatter that checks for extra keys."""

    def check_unused_args(
        self,
        used_args: Sequence[Union[int, str]],
        args: Sequence,
        kwargs: Mapping[str, Any],
    ) -> None:
        """Check to see if extra parameters are passed."""
        extra = set(kwargs).difference(used_args)
        if extra:
            raise KeyError(extra)


@lru_cache(maxsize=2000)
def hash_text(*text: str) -> str:
    bs = [t.encode() if not isinstance(t, bytes) else t for t in text]
    return xxhash.xxh3_128_hexdigest(b"".join(bs))


VERSION_NUMBERS = re.compile(r"\b\d+\.\d+(?:\.\d+)?\w*\b")


def tokenize(text: str) -> list[int]:
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return tokenizer.encode(text)


def detokenize(tokens: list[int]) -> str:
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
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
) -> str | tuple[str, int]:
    """
    Split a text into a list of strings. Chunks are split by tokens.

    Args:
        text (str): The text to split.
        chunk_size (int): The number of tokens in each chunk.
        chunk_overlap (float): The fraction of overlap between chunks.
        last_chunk_threshold (float): If the last chunk is less than this fraction of
            the chunk_size, it will be added to the prior chunk
        return_index (bool): If True, return a tuple of (chunk, index) where index is the
            character index of the start of the chunk in the original text.
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


def _extract_keywords(text: str, n_keywords: int = None) -> list[str]:
    # deferred import
    import yake

    kw = yake.KeywordExtractor(
        lan="en",
        n=1,
        dedupLim=0.9,
        dedupFunc="seqm",
        windowsSize=1,
        top=n_keywords or marvin.settings.default_n_keywords,
        features=None,
    )
    keywords = kw.extract_keywords(text)
    # return only keyword, not score
    return [k[0] for k in keywords]


async def extract_keywords(text: str, n_keywords: int = None) -> list[str]:
    # keyword extraction can take a while and is blocking
    return await marvin.utilities.async_utils.run_async_process(
        _extract_keywords, text=text, n_keywords=n_keywords
    )
    # return _extract_keywords(text=text, n_keywords=n_keywords)


def create_minimap_fn(content: str) -> Callable[[int], str]:
    """
    Given a document with markdown headers, returns a function that outputs the current headers
    for any character position in the document.
    """
    minimap: dict[int, str] = {}
    in_code_block = False
    current_stack = {}
    characters = 0
    for line in content.splitlines():
        characters += len(line)
        if line.startswith("```"):
            in_code_block = not in_code_block
        if in_code_block:
            continue

        if line.startswith("# "):
            current_stack = {1: line}
        elif line.startswith("## "):
            for i in range(2, 6):
                current_stack.pop(i, None)
            current_stack[2] = line
        elif line.startswith("### "):
            for i in range(3, 6):
                current_stack.pop(i, None)
            current_stack[3] = line
        elif line.startswith("#### "):
            for i in range(4, 6):
                current_stack.pop(i, None)
            current_stack[4] = line
        elif line.startswith("##### "):
            for i in range(5, 6):
                current_stack.pop(i, None)
            current_stack[5] = line
        else:
            continue

        minimap[characters - len(line)] = current_stack

    def get_location_fn(n: int) -> str:
        if n < 0:
            raise ValueError("n must be >= 0")
        # get the stack of headers that is closest to - but before - the current position
        stack = minimap.get(max((k for k in minimap if k <= n), default=0), {})

        ordered_stack = [stack.get(i) for i in range(1, 6)]
        return "\n".join([s for s in ordered_stack if s is not None])

    return get_location_fn
