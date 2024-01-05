from typing import TypeVar

import marvin

T = TypeVar("T")


def cast(text: str, _type: type[T], instructions: str = None) -> T:
    return marvin.model(_type)(text, instructions=instructions)


def extract(text: str, _type: type[T], instructions: str = None) -> list[T]:
    @marvin.fn
    def _extract(text: str) -> list[_type]:
        msg = "Extract a list of objects from the text, using inference if necessary."
        if instructions:
            msg += f' Follow these instructions for extraction: "{instructions}"'
        return msg

    return _extract(text)


def classify(text: str, _type: type[T], instructions: str = None) -> dict[str, T]:
    @marvin.components.classifier
    def _classify(text: str) -> _type:
        if instructions:
            return f'Follow these instructions for classification: "{instructions}"'

    return _classify(text)
