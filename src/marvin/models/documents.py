import pendulum
from pydantic import Field, confloat, validator
from typing_extensions import Literal

import marvin
from marvin.models.ids import DocumentID
from marvin.utilities.strings import (
    count_tokens,
    create_minimap_fn,
    extract_keywords,
    split_text,
)
from marvin.utilities.types import MarvinBaseModel

DocumentType = Literal["original", "excerpt", "summary"]


EXCERPT_TEMPLATE = """
The following is a {document.type} document:
# Document metadata
{document.metadata}
# Document keywords
{keywords}
# Excerpt's location in document
{minimap}
# Excerpt contents:
{excerpt}
"""


class Document(MarvinBaseModel):
    """A source of information that is storable & searchable.

    Anything that can be represented as text can be stored as a document:
    web pages, git repos / issues, PDFs, and even just plain text files.

    A document is a unit of information that can be stored in a topic, and
    should be produced with a `Loader` of some kind.

    Documents can be originals, excerpts or summaries of other documents, which
    determines their `type`.
    """

    id: str = Field(default_factory=DocumentID.new)
    text: str = Field(
        ..., description="Any text content that you want to keep / embed."
    )
    embedding: list[float] | None = Field(default=None)
    metadata: dict | None = Field(default=None)

    source: str = Field(default="unknown")
    type: DocumentType = Field(default="original")
    parent_document_id: DocumentID | None = Field(default=None)
    topic_name: str = Field(default=marvin.settings.default_topic)
    tokens: int | None = Field(default=None)
    order: int | None = Field(default=None)
    keywords: list[str] = Field(default_factory=list)

    @validator("tokens")
    def validate_tokens(cls, v, values):
        if not v:
            return count_tokens(values["text"])
        return v

    @validator("metadata")
    def add_timestamp(cls, v):
        if v and "created_at" not in v:
            v["created_at"] = pendulum.now().isoformat()
        return v

    @validator("source")
    def add_source(cls, v, values):
        if values["metadata"] and "source" in values["metadata"]:
            return values["metadata"]["source"]
        return v

    @property
    def hash(self):
        return marvin.utilities.strings.hash_text(self.text)

    async def to_excerpts(
        self, chunk_tokens: int = 400, overlap: confloat(ge=0, le=1) = 0.1
    ) -> list["Document"]:
        """
        Create document excerpts by chunking the document text into regularly-sized
        chunks and adding a "minimap" directory to the top.
        """
        minimap_fn = create_minimap_fn(self.text)
        excerpts = []

        for i, (text, chr) in enumerate(
            split_text(
                text=self.text,
                chunk_size=chunk_tokens,
                chunk_overlap=overlap,
                return_index=True,
            )
        ):
            keywords = await extract_keywords(text)

            excerpt_text = EXCERPT_TEMPLATE.format(
                excerpt=text,
                document=self,
                keywords=", ".join(keywords),
                minimap=minimap_fn(chr),
            ).strip()

            excerpt_metadata = self.metadata.copy()
            excerpt_metadata.update({"document_type": "excerpt"})
            excerpts.append(
                Document(
                    type="excerpt",
                    parent_document_id=self.id,
                    text=excerpt_text,
                    order=i,
                    keywords=keywords,
                    topic_name=marvin.settings.default_topic,
                    metadata=excerpt_metadata,
                    tokens=count_tokens(excerpt_text),
                )
            )
        return excerpts
