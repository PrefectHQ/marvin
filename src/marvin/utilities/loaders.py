from pydantic import confloat

import marvin
from marvin.models.documents import Document
from marvin.models.excerpts import Excerpt
from marvin.models.ids import ExcerptID
from marvin.utilities.strings import (
    count_tokens,
    create_minimap_fn,
    extract_keywords,
    split_text,
)

EXCERPT_TEMPLATE = """
The following is an excerpt from a {document.type} called "{document.chroma_id}". 
# Document details
{document.metadata}
# Document keywords
{keywords}
# Excerpt's location in document
{minimap}
# Excerpt
{excerpt}
"""


async def create_excerpts_from_split_text(
    document: Document, chunk_tokens: int = 400, overlap: confloat(ge=0, le=1) = 0.1
) -> list[Excerpt]:
    """
    Create document excerpts by chunking the document text into regularly-sized
    chunks and adding a "minimap" directory to the top.
    """
    minimap_fn = create_minimap_fn(document.text)
    excerpts = []

    for i, (text, chr) in enumerate(
        split_text(
            document.text,
            chunk_size=chunk_tokens,
            chunk_overlap=overlap,
            return_index=True,
        )
    ):
        keywords = await extract_keywords(text)

        excerpt_id = ExcerptID.new()
        excerpt_text = EXCERPT_TEMPLATE.format(
            excerpt=text,
            document=document,
            keywords=", ".join(keywords),
            minimap=minimap_fn(chr),
        ).strip()

        excerpts.append(
            Excerpt(
                id=excerpt_id,
                text=excerpt_text,
                tokens=count_tokens(excerpt_text),
                order=i,
                keywords=keywords,
                document_id=document.id,
                topic_name=marvin.settings.default_topic,
                document_metadata=document.metadata,
            )
        )
    return excerpts
