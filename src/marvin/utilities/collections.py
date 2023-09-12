"""
Document Batching and File Selection Utilities
==============================================

This module provides utility functions to facilitate the batch processing of documents 
and efficient file selection based on provided glob patterns. It's especially tailored 
for splitting large documents into smaller batches and selectively loading documents 
into vector stores.

Key Functions:
--------------
- `split_into_batches`: Divides an iterable (like documents) into smaller batches, 
either based on a fixed count or a custom size function.
- `select_files_from_directory`: Selectively retrieves files from a directory based on inclusion and exclusion glob patterns.

Note:
-----
For the most effective use, consider the specific requirements of the vector store and the nature of the documents.
"""  # noqa: E501

import itertools
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, TypeVar

T = TypeVar("T")


def split_into_batches(
    iterable: Iterable[T],
    batch_size: int,
    size_function: Optional[Callable[[Any], int]] = None,
) -> Iterable[List[T]]:
    """
    Divides an iterable into smaller batches based on a given size.

    Args:
    - iterable (Iterable[T]): The input iterable, e.g., a list of documents.
    - batch_size (int): The desired size for each batch.
    - size_function (Optional[Callable]): A function to compute the size of an item.
      If not provided, the batch size is determined by the number of items.

    Returns:
    - Iterable[List[T]]: Batches of items from the input iterable.

    Note:
    If an item's size exceeds the desired batch size, it will be returned as its own batch.
    """  # noqa: E501

    if size_function is None:
        iterator = iter(iterable)
        while True:
            batch = list(itertools.islice(iterator, batch_size))
            if not batch:
                break
            yield batch
    else:
        batch = []
        current_batch_size = 0
        for item in iterable:
            batch.append(item)  # type: ignore
            current_batch_size += size_function(item)
            if current_batch_size > batch_size:
                yield batch
                batch = []
                current_batch_size = 0
        if batch:
            yield batch


def select_files_from_directory(
    directory: Optional[str] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> List[Path]:
    """
    Selectively retrieves files from a directory based on glob patterns.

    Args:
    - directory (Optional[str]): The target directory. Defaults to the current directory.
    - include_patterns (Optional[List[str]]): Glob patterns for files to include. Defaults to all files.
    - exclude_patterns (Optional[List[str]]): Glob patterns for files to exclude. Defaults to '.git' directory.

    Returns:
    - List[Path]: A list of file paths that match the include patterns and don't match the exclude patterns.
    """  # noqa: E501

    include_patterns = include_patterns or ["**/*"]
    exclude_patterns = exclude_patterns or [".git/**/*"]

    directory_path = Path(directory) if directory else Path.cwd()

    if not directory_path.is_dir():
        raise ValueError(f"'{directory}' is not a directory.")

    def files_from_patterns(patterns: List[str]) -> set[Any]:
        return {
            file
            for pattern in patterns
            for file in directory_path.glob(pattern)
            if file.is_file()
        }

    matching_files = files_from_patterns(include_patterns) - files_from_patterns(
        exclude_patterns
    )

    return [file.relative_to(directory_path) for file in matching_files]


batched = split_into_batches
multi_glob = select_files_from_directory
