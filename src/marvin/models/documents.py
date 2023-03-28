import inspect

from jinja2 import Template
from pydantic import Field, confloat, validator
from typing_extensions import Literal

import marvin
from marvin.models.ids import DocumentID
from marvin.models.metadata import Metadata
from marvin.utilities.strings import (
    count_tokens,
    create_minimap_fn,
    extract_keywords,
    jinja_env,
    split_text,
)
from marvin.utilities.types import MarvinBaseModel

DocumentType = Literal["original", "excerpt", "summary"]


EXCERPT_TEMPLATE = jinja_env.from_string(
    inspect.cleandoc(
        """The following is a {{ document.type }} document {% if document.source %}produced by {{ document.source }}
        {% endif %}
        {% if document.metadata %}\n\n# Document metadata
        {{ document.metadata }}
        {% endif %}
        {% if document.keywords %}
        # Document keywords
        {{ document.keywords }}
        {% endif %}
        {% if minimap %}
        # Excerpt's location in document
        {{ minimap }}
        {% endif %}# Excerpt content: {{ excerpt_text }}"""  # noqa: E501
    )
)


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
    metadata: Metadata | None = Field(default=None)

    source: str | None = Field(default=None)
    type: DocumentType = Field(default="original")
    parent_document_id: DocumentID | None = Field(default=None)
    topic_name: str = Field(default=marvin.settings.default_topic)
    tokens: int | None = Field(default=None)
    order: int | None = Field(default=None)
    keywords: list[str] = Field(default_factory=list)

    @validator("tokens", pre=True, always=True)
    def validate_tokens(cls, v, values):
        if not v:
            return count_tokens(values["text"])
        return v

    @property
    def hash(self):
        return marvin.utilities.strings.hash_text(self.text)

    async def to_excerpts(
        self,
        excerpt_template: Template = None,
        chunk_tokens: int = 200,
        overlap: confloat(ge=0, le=1) = 0.1,
        **extra_template_kwargs,
    ) -> list["Document"]:
        """
        Create document excerpts by chunking the document text into regularly-sized
        chunks and adding a "minimap" directory to the top.

        Args:
            excerpt_template: A jinja2 template to use for rendering the excerpt.
            chunk_tokens: The number of tokens to include in each excerpt.
            overlap: The fraction of overlap between each excerpt.

        """
        minimap_fn = create_minimap_fn(self.text)
        excerpts = []

        if not excerpt_template:
            excerpt_template = EXCERPT_TEMPLATE

        for i, (text, chr) in enumerate(
            split_text(
                text=self.text,
                chunk_size=chunk_tokens,
                chunk_overlap=overlap,
                return_index=True,
            )
        ):
            keywords = await extract_keywords(text)

            minimap = (  # only include minimap if document is markdown
                minimap_fn(chr)
                if self.metadata
                and "link" in self.metadata.__fields__
                and self.metadata.link.endswith(".md")
                else None
            )

            excerpt_text = excerpt_template.render(
                document=self,
                excerpt_text=text,
                keywords=", ".join(keywords),
                minimap=minimap,
                **extra_template_kwargs,
            )

            excerpt_metadata = self.metadata.copy() if self.metadata else Metadata()
            excerpt_metadata.document_type = "excerpt"
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
