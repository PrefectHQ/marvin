from typing import TypeVar

import marvin

# from marvin.components.model import model

T = TypeVar("T")


def cast(text: str, _type: type[T], instructions: str = None) -> T:
    return marvin.model(_type, instructions=instructions)(text)


def extract(text: str, _type: type[T], instructions: str = None) -> list[T]:
    @marvin.fn
    def _extract(text: str) -> list[_type]:
        if instructions:
            return (
                "Extract a list of objects from the text, matching the following"
                f' instructions or guidance: "{instructions}"'
            )
        else:
            return "Extract a list of objects from the text."

    return _extract(text)
    # return marvin.model(list[_type], instructions=instructions)(text)


def classify(text: str, _type: type[T], instructions: str = None) -> dict[str, T]:
    @marvin.components.classifier
    def _classify(text: str) -> _type:
        if instructions:
            return (
                "Extract a list of objects from the text, matching the following"
                f' instructions or guidance: "{instructions}"'
            )
        else:
            return "Extract a list of objects from the text."

    return _classify(text)
