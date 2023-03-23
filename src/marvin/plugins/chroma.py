import pendulum

from marvin.infra.chroma import Chroma
from marvin.plugins import Plugin


async def query_chroma(query: str, where: dict, n: int = 4):
    if where and "created_at" in where:
        where["created_at"] = {
            op: pendulum.parse(value).timestamp()
            for op, value in where["created_at"].items()
        }

    print(where)

    async with Chroma() as chroma:
        query_result = await chroma.query(
            query_texts=[query],
            n_results=n,
            include=["documents"],
            where={**(where or {}), "document_type": "excerpt"},
        )
        excerpts = [
            excerpt for excerpts in query_result["documents"] for excerpt in excerpts
        ]

    return "\n\n".join(excerpt for excerpt in excerpts)


class ChromaSearch(Plugin):
    description: str = "Semantic search for relevant documents."

    async def run(self, query: str, where: dict | None = None) -> str:
        return await query_chroma(query, where)
