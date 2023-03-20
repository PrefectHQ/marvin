from pydantic import Field

from marvin.models.ids import ExcerptID
from marvin.utilities.types import MarvinBaseModel


class Excerpt(MarvinBaseModel):
    """An excerpt from a document."""

    id: ExcerptID = Field(default_factory=ExcerptID.new)
    text: str = Field(None)
    tokens: int = Field(None)
    order: int = Field(None)
    keywords: list[str] = Field(default_factory=list)

    topic_name: str = Field(None)
    document_id: str = Field(None)
    document_metadata: dict | None = Field(default=None)
