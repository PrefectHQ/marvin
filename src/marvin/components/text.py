from typing import TypeVar

from marvin.components.model import model

T = TypeVar("T")


def cast(text: str, _type: type[T]) -> T:
    return model(_type)(text)


def extract(text: str, _type: type[T]) -> list[T]:
    return model(list[_type])(text)
