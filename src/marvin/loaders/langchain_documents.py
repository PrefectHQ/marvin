import asyncio
from typing import List

from langchain.docstore.document import Document as LangChainDocument
from pydantic import Field

from marvin.loaders.base import Loader
from marvin.models.documents import Document
from marvin.models.metadata import Metadata


class LangChainLoader(Loader):
    """
    A loader for `langchain` documents.

    Example:
        Use any langchain loader to load `Document` objects
        ```
        import asyncio
        import marvin
        from marvin.loaders.langchain_documents import LangChainLoader

        marvin.settings.log_level = "DEBUG"

        from langchain.document_loaders.directory import DirectoryLoader

        langchain_documents = DirectoryLoader(".", silent_errors=True).load()

        documents = asyncio.run(LangChainLoader(documents=langchain_documents).load())

        print(documents[0])
        ```
    """

    documents: List[LangChainDocument] = Field(...)
    metadatas: List[Metadata] = Field(default_factory=list)

    async def load(self) -> list[Document]:
        documents = [
            Document(
                text=doc.page_content,
                metadata=self.metadatas[i]
                if self.metadatas
                else Metadata.parse_obj(doc.metadata),
            )
            for i, doc in enumerate(self.documents)
        ]

        return [
            excerpt
            for excerpts in await asyncio.gather(
                *[doc.to_excerpts() for doc in documents]
            )
            for excerpt in excerpts
        ]
