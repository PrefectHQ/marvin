import pendulum
from pydantic import Field, root_validator

from marvin.infra.chroma import Chroma
from marvin.plugins import Plugin


async def query_chroma(query: str, where: dict, n: int = 4) -> str:
    if where and "created_at" in where:
        where["created_at"] = {
            op: pendulum.parse(value).timestamp()
            for op, value in where["created_at"].items()
        }

    async with Chroma() as chroma:
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

    @root_validator
    def validate(cls, values):
        if values["keywords"]:
            values["description"] += (
                " Useful for answering questions that refer to the following keywords:"
                f" {', '.join(values['keywords'])}"
            )
        return values

    async def run(self, query: str) -> str:
        return await query_chroma(query, where=None)


class ChromaSearch(SimpleChromaSearch):
    async def run(self, query: str, where: dict | None) -> str:
        return await query_chroma(query, where=where)
