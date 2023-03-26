import pendulum
from pydantic import Field

import marvin
from marvin.config import temporary_settings
from marvin.infra.chroma import Chroma
from marvin.plugins import Plugin


async def query_chroma(query: str, where: dict, n: int = 4) -> str:
    if where and "created_at" in where:
        where["created_at"] = {
            op: pendulum.parse(value).timestamp()
            for op, value in where["created_at"].items()
        }

    async with Chroma(settings=marvin.settings.chroma) as chroma:
        query_result = await chroma.query(
            query_texts=[query],
            n_results=n,
            include=["documents"],
            where={**(where or {}), "document_type": "excerpt"},
        )

    return "\n\n".join(
        excerpt for excerpts in query_result["documents"] for excerpt in excerpts
    )


class SimpleChromaSearch(Plugin):
    description: str = (
        "Semantic search for relevant documents."
        " To use this plugin, simply provide a natural language `query`"
        " and relevant document excerpts will be returned to you."
    )

    keywords: list[str] = Field(default_factory=list)

    def get_full_description(self) -> str:
        base_description = super().get_full_description()
        if self.keywords:
            return (
                base_description
                + " Useful for answering questions that refer to the following"
                " keywords:"
                f" {', '.join(self.keywords)}"
            )
        return base_description

    async def run(self, query: str) -> str:
        with temporary_settings(openai_model_temperature=0.2):
            return await query_chroma(query, where=None)


class ChromaSearch(SimpleChromaSearch):
    async def run(self, query: str, where: dict | None) -> str:
        return await query_chroma(query, where=where)
