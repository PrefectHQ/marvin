import pendulum
from pydantic import Field

from marvin.config import temporary_settings
from marvin.infra.chroma import Chroma
from marvin.plugins import Plugin
from marvin.utilities.strings import extract_keywords


def build_metadata_filter(where: dict, operator: str = "$and") -> dict:
    filters = []
    for key, value in where.items():
        if key == "created_at":
            filters.append(
                {
                    "created_at": {
                        k: pendulum.parse(v).timestamp() for k, v in value.items()
                    }
                }
            )
        else:
            filters.append({key: value})

    if len(filters) == 1:
        return filters[0]
    return {operator: filters}


def build_document_filter(keywords: list[str]) -> dict:
    filters = [{"$contains": keyword} for keyword in keywords]
    return {"$or": filters}


async def query_chroma(query: str, where: dict, n: int = 4) -> str:
    keywords = await extract_keywords(query)

    query_kwargs = dict(
        query_texts=[query],
        n_results=n,
        include=["documents"],
        where=build_metadata_filter(where) if where else None,
        where_document=build_document_filter(keywords) if keywords else None,
    )

    async with Chroma() as chroma:
        query_result = await chroma.query(**query_kwargs)

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
