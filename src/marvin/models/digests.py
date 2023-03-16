from pydantic import Field

from marvin.models.base import MarvinBaseModel


class Digest(MarvinBaseModel):
    ids: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    embeddings: list[list[float]] | None = Field(default=None)
    metadatas: list[dict] = Field(default_factory=list)
