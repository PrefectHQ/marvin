import itertools
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
)

import xxhash
from openai.types import CreateEmbeddingResponse
from prefect.utilities.collections import distinct

from marvin.utilities.asyncio import run_sync_if_awaitable

T = TypeVar("T")

if TYPE_CHECKING:
    from marvin._rag.documents import Document


def generate_prefixed_uuid(prefix: str) -> str:
    """Generate a UUID string with the given prefix."""
    if "_" in prefix:
        raise ValueError("Prefix must not contain underscores.")
    return f"{prefix}_{uuid.uuid4()}"


def batched(
    iterable: Iterable[T], size: int, size_fn: Callable[[Any], int] = None
) -> Iterable[T]:
    """
    If size_fn is not provided, then the batch size will be determined by the
    number of items in the batch.

    If size_fn is provided, then it will be used
    to compute the batch size. Note that if a single item is larger than the
    batch size, it will be returned as a batch of its own.
    """
    if size_fn is None:
        it = iter(iterable)
        while True:
            batch = tuple(itertools.islice(it, size))
            if not batch:
                break
            yield batch
    else:
        batch = []
        batch_size = 0
        for item in iter(iterable):
            batch.append(item)
            batch_size += size_fn(item)
            if batch_size > size:
                yield batch
                batch = []
                batch_size = 0
        if batch:
            yield batch


def multi_glob(
    directory: str | None = None,
    keep_globs: List[str] | None = None,
    drop_globs: List[str] | None = None,
) -> List[Path]:
    """
    Return a list of all files in the given directory that match the
    patterns in keep_globs and do not match the patterns in drop_globs.
    The patterns are defined using glob syntax.
    """
    keep_globs = keep_globs or ["**/*"]
    drop_globs = drop_globs or [".git/**/*"]
    directory_path = Path(directory) if directory else Path.cwd()

    if not directory_path.is_dir():
        raise ValueError(f"'{directory}' is not a directory.")

    def files_from_globs(globs: List[str]) -> Set[Path]:
        return {
            file
            for pattern in globs
            for file in directory_path.glob(pattern)
            if file.is_file()
        }

    matching_files = files_from_globs(keep_globs) - files_from_globs(drop_globs)
    return [file.relative_to(directory_path) for file in matching_files]


def rm_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def rm_text_after(text: str, substring: str) -> str:
    return (
        text[: start + len(substring)]
        if (start := text.find(substring)) != -1
        else text
    )


def html_to_content(
    html: str, parsing_fn: Optional[Callable[[str], str]] = None
) -> str:
    if parsing_fn is None:
        raise ValueError("A parsing function must be provided.")

    return run_sync_if_awaitable(parsing_fn(html))


def extract_keywords(text: str) -> list[str]:
    try:
        import yake
    except ImportError:
        raise ImportError(
            "yake is required for keyword extraction. Please install it with"
            " `pip install `marvin[rag]` or `pip install yake`."
        )

    kw = yake.KeywordExtractor(
        lan="en",
        n=1,
        dedupLim=0.9,
        dedupFunc="seqm",
        windowsSize=1,
        top=10,
        features=None,
    )

    return [k[0] for k in kw.extract_keywords(text)]


@lru_cache(maxsize=2048)
def hash_text(*text: str) -> str:
    bs = [t.encode() if not isinstance(t, bytes) else t for t in text]
    return xxhash.xxh3_128_hexdigest(b"".join(bs))


def get_distinct_documents(documents: Iterable["Document"]) -> Iterable["Document"]:
    """Return a list of distinct documents."""
    return distinct(documents, key=lambda doc: doc.hash)


async def create_openai_embeddings(
    input_: Union[str, List[str]],
    timeout: int = 60,
    model: str = "text-embedding-ada-002",
) -> Union[List[float], List[List[float]]]:
    """Create OpenAI embeddings for a list of texts."""

    try:
        import numpy  # noqa F401 # type: ignore
    except ImportError:
        raise ImportError(
            "The numpy package is required to create OpenAI embeddings. Please install"
            " it with `pip install numpy`."
        )
    from marvin.client.openai import AsyncMarvinClient

    if isinstance(input_, str):
        input_ = [input_]
    elif not isinstance(input_, list):
        raise TypeError(
            f"Expected input to be a str or a list of str, got {type(input_).__name__}."
        )

    embedding: CreateEmbeddingResponse = (
        await AsyncMarvinClient().client.embeddings.create(
            input=input_, model=model, timeout=timeout
        )
    )

    if len(embedding.data) == 1:
        return embedding.data[0].embedding

    return [data.embedding for data in embedding.data]
