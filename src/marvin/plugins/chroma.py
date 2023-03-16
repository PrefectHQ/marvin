from marvin.infra.chroma import Chroma
from marvin.plugins import Plugin
from marvin.utilities.strings import slice_tokens


async def query_chroma(query: str, n: int = 4):
    chroma = Chroma()
    results = await chroma.query(
        query_texts=[query],
        n_results=n,
        include=["documents"],
    )
    summary = "\n\n".join(
        f"({link}): {doc}" for link, doc in zip(results["ids"], results["documents"])
    )

    return slice_tokens(summary, 2000)


class ChromaVectorstore(Plugin):
    description: str = (
        "Search Chroma for documents that are similar to a user query - "
        "Use this plugin when asked about Prefect-related things."
    )

    async def run(self, query: str) -> str:
        return await query_chroma(query)
