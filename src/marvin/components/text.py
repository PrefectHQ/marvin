from typing import TypeVar

import marvin

T = TypeVar("T")


def cast(text: str, _type: type[T], instructions: str = None) -> T:
    """Cast the text to the provided type.

    Args:
        text: The text to be cast.
        _type: The type to cast the text to.
        instructions: Instructions to follow for casting.

    Returns:
        An instance of the provided `_type` according to the provided `text` and `instructions`.

    Example:
        ```python
        import marvin
        from typing_extensions import TypedDict

        class Person(TypedDict):
            name: str
            description: str
            age: int | None
            occupation: str | None

        marvin.cast("hi this is Jake from State Farm, im wearing khakis", Person)
        '''
        {
            'name': 'Jake',
            'description': 'im wearing khakis',
            'age': None,
            'occupation': 'State Farm'
        }
        '''
        ```
    """
    return marvin.model(_type)(text, instructions=instructions)


def extract(text: str, _type: type[T], instructions: str = None) -> list[T]:
    """Extract a list of objects from the text, using inference if necessary.

    Args:
        text: The text to be extracted from.
        _type: The type of objects to extract.
        instructions: Instructions to follow for extraction.

    Returns:
        A list of objects of the provided `_type` according to the provided `text` and `instructions`.

    Example:
        ```python
        import marvin
        from typing_extensions import TypedDict

        class Location(TypedDict):
            city: str
            lat: float
            lon: float

        marvin.extract(
            "I drove from the big apple to the windy city",
            Location,
            instructions="only real city names allowed",
        )
        '''
        [{'city': 'New York', 'lat': 40.7128, 'lon': -74.006},
        {'city': 'Chicago', 'lat': 41.8781, 'lon': -87.6298}]
        '''
        ```

    """

    @marvin.fn
    def _extract(text: str) -> list[_type]:
        msg = "Extract a list of objects from the text, using inference if necessary."
        if instructions:
            msg += f' Follow these instructions for extraction: "{instructions}"'
        return msg

    return _extract(text)


def classify(text: str, _type: type[T], instructions: str = None) -> T:
    """Classify the text as the provided type.

    Args:
        text: The text to be classified.
        _type: The type to classify the text as.
        instructions: Instructions to follow for classification.

    Returns:
        An instance of the provided `_type` according to the provided `text` and `instructions`.

    Example:
        ```python
        from enum import Enum
        import marvin

        class GitHubIssueTag(Enum):
            BUG = "bug"
            FEATURE = "feature"
            ENHANCEMENT = "enhancement"
            DOCS = "docs"

        marvin.classify("I think your docs are out of date", GitHubIssueTag)
        '''
        <GitHubIssueTag.DOCS: 'docs'>
        '''
        ```
    """

    @marvin.components.classifier
    def _classify(text: str) -> _type:
        if instructions:
            return f'Follow these instructions for classification: "{instructions}"'

    return _classify(text)
