import itertools
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, TypeVar

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

    Args:
        iterable: The iterable to batch.
        size: The size of each batch.
        size_fn: A function that takes an item from the iterable and returns its size.

    Returns:
        An iterable of batches.

    Example:
        Batch a list of integers into batches of size 2:
        ```python
        batched([1, 2, 3, 4, 5], 2)
        # [[1, 2], [3, 4], [5]]
        ```
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
    directory: Optional[str] = None,
    keep_globs: Optional[list[str]] = None,
    drop_globs: Optional[list[str]] = None,
) -> list[Path]:
    """Return a list of files in a directory that match the given globs.

    Args:
        directory: The directory to search. Defaults to the current working directory.
        keep_globs: A list of globs to keep. Defaults to ["**/*"].
        drop_globs: A list of globs to drop. Defaults to [".git/**/*"].

    Returns:
        A list of `Path` objects in the directory that match the given globs.

    Example:
        Recursively find all Python files in the `src` directory:
        ```python
        all_python_files = multi_glob(directory="src", keep_globs=["**/*.py"])
        ```
    """
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
