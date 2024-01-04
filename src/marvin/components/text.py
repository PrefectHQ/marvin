from typing import TypeVar

import marvin

# from marvin.components.model import model

T = TypeVar("T")


def cast(text: str, _type: type[T]) -> T:
    return marvin.model(_type)(text)


def extract(text: str, _type: type[T]) -> list[T]:
    return marvin.model(list[_type])(text)


def classify(text: str, _type: type[T]) -> dict[str, T]:
    @marvin.classifier
    def _classify(text: str) -> _type:
        """Classify the text"""

    return _classify(text)
