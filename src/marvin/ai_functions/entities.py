from typing import TypeVar, Union

from pydantic import Field

from marvin.ai_functions import ai_fn
from marvin.utilities.types import MarvinBaseModel

T = TypeVar("T")


@ai_fn
def extract_keywords(text: str) -> list[str]:
    """
    Extract the most important keywords from the given `text`. Choose words that
    best characterize its content. If there are no keywords, return an empty
    list.
    """


class NamedEntity(MarvinBaseModel):
    entity: str = Field(description="The entity name")
    type: str = Field(description="The entity type (based on spaCy NER types)")


@ai_fn
def extract_named_entities(text: str) -> list[NamedEntity]:
    """
    Extract named entities from the given `text` and return a list of
    NamedEntity objects. Correct capitalization if needed.
    """


def extract_types(text: str, types: list[type[T]]) -> list[T]:
    """
    Given text, extract entities of the given `types` in a single pass and
    return a list of matched objects.
    """
    if len(types) > 1:
        types = Union[tuple(types)]

    @ai_fn
    def _extract(text: str) -> list[types]:
        """
        Extract entities from the given `text` and return a list of any objects
        that match any of the provided `types`. Correct capitalization if needed.
        """

    return _extract(text)
