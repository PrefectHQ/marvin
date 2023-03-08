import itertools
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
