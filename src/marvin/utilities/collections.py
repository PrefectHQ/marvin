import itertools
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

T = TypeVar("T")


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


def multi_glob(directory=None, keep_globs=None, drop_globs=None) -> list[Path]:
    keep_globs = keep_globs or ["**/*"]
    drop_globs = drop_globs or [".git/**/*"]

    directory_path = Path(directory) if directory else Path.cwd()

    if not directory_path.is_dir():
        raise ValueError(f"'{directory}' is not a directory.")

    def files_from_globs(globs):
        return {
            file
            for pattern in globs
            for file in directory_path.glob(pattern)
            if file.is_file()
        }

    matching_files = files_from_globs(keep_globs) - files_from_globs(drop_globs)

    return [file.relative_to(directory_path) for file in matching_files]
