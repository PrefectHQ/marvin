from marvin.infra.chroma import Chroma
from marvin.plugins import Plugin


async def query_chroma(query: str, n: int = 4):
    chroma = Chroma(collection_name="marvin")
    results = await chroma.query(
        query_texts=[query],
        n_results=n,
        include=["documents"],
        where={"document_type": "excerpt"},
    )

    return "\n\n".join(
        excerpt for excerpts in results["documents"] for excerpt in excerpts
    )


class ChromaSearch(Plugin):
    description: str = "Semantic search for relevant documents."

    async def run(self, query: str) -> str:
        return await query_chroma(query)
